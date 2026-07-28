"""
CatBoost Training Pipeline for Passenger Demand Forecasting
Uses synthetic_passenger_demand.csv with all features and chronological split.
"""

import os
import json
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor, Pool
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import logging

from config import config
from data_preprocessing import DataPreprocessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CatBoostTrainer:
    """Trains CatBoost model for passenger demand forecasting."""
    
    def __init__(self):
        """Initialize the trainer."""
        self.preprocessor = DataPreprocessor()
        self.model = None
        self.feature_names = None
        self.categorical_features = None
        self.metrics = {}
        
        # Ensure output directories exist
        config.ensure_directories()
    
    def load_and_split_data(self) -> tuple:
        """
        Load dataset and split chronologically.
        
        Returns:
            Tuple of (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        logger.info("Loading and splitting data...")
        
        # Load dataset
        df = self.preprocessor.load_dataset()
        
        # Chronological split
        train_df, val_df, test_df = self.preprocessor.split_chronologically(df)
        
        # Prepare features for each split
        X_train, y_train, cat_features = self.preprocessor.prepare_features(train_df, for_training=True)
        X_val, y_val, _ = self.preprocessor.prepare_features(val_df, for_training=True)
        X_test, y_test, _ = self.preprocessor.prepare_features(test_df, for_training=True)
        
        # Store feature info
        self.feature_names = self.preprocessor.get_feature_names()
        self.categorical_features = self.preprocessor.get_categorical_features()
        
        logger.info(f"Training samples: {len(X_train)}")
        logger.info(f"Validation samples: {len(X_val)}")
        logger.info(f"Test samples: {len(X_test)}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> CatBoostRegressor:
        """
        Train CatBoost model with early stopping.
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            
        Returns:
            Trained CatBoost model
        """
        logger.info("Training CatBoost model...")
        
        # Create CatBoost pools
        train_pool = Pool(
            data=X_train,
            label=y_train,
            cat_features=self.categorical_features
        )
        
        val_pool = Pool(
            data=X_val,
            label=y_val,
            cat_features=self.categorical_features
        )
        
        # Initialize model
        self.model = CatBoostRegressor(
            iterations=config.get('iterations', 1000),
            learning_rate=config.get('learning_rate', 0.05),
            depth=config.get('depth', 8),
            l2_leaf_reg=config.get('l2_leaf_reg', 3.0),
            loss_function=config.get('loss_function', 'RMSE'),
            eval_metric=config.get('eval_metric', 'RMSE'),
            random_seed=config.get('random_seed', 42),
            verbose=config.get('verbose', 100),
            early_stopping_rounds=config.get('early_stopping_rounds', 100),
            task_type='CPU',
            thread_count=-1
        )
        
        # Train model
        self.model.fit(
            train_pool,
            eval_set=val_pool,
            use_best_model=True
        )
        
        logger.info(f"Model training completed. Best iteration: {self.model.best_iteration_}")
        
        return self.model
    
    def evaluate_model(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> dict:
        """
        Evaluate model on test set.
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Dictionary of evaluation metrics
        """
        logger.info("Evaluating model...")
        
        # Create test pool
        test_pool = Pool(
            data=X_test,
            cat_features=self.categorical_features
        )
        
        # Make predictions
        y_pred = self.model.predict(test_pool)
        
        # Calculate metrics
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # MAPE (handle division by zero)
        mape = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1))) * 100
        
        self.metrics = {
            'RMSE': float(rmse),
            'MAE': float(mae),
            'R2': float(r2),
            'MAPE': float(mape),
            'best_iteration': int(self.model.best_iteration_),
            'n_features': len(self.feature_names),
            'n_categorical': len(self.categorical_features)
        }
        
        logger.info(f"RMSE: {rmse:.4f}")
        logger.info(f"MAE: {mae:.4f}")
        logger.info(f"R2: {r2:.4f}")
        logger.info(f"MAPE: {mape:.2f}%")
        
        return self.metrics
    
    def save_model(self) -> str:
        """
        Save trained model to disk.
        
        Returns:
            Path to saved model
        """
        logger.info("Saving model...")
        
        model_dir = config.get('model_dir')
        model_path = os.path.join(model_dir, 'catboost_demand_model.cbm')
        
        self.model.save_model(model_path)
        logger.info(f"Model saved to {model_path}")
        
        return model_path
    
    def save_metrics(self) -> str:
        """
        Save training metrics to JSON.
        
        Returns:
            Path to metrics file
        """
        logger.info("Saving metrics...")
        
        output_dir = config.get('output_dir')
        metrics_path = os.path.join(output_dir, 'training_metrics.json')
        
        # Add timestamp
        self.metrics['timestamp'] = datetime.now().isoformat()
        self.metrics['feature_names'] = self.feature_names
        self.metrics['categorical_features'] = self.categorical_features
        
        with open(metrics_path, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        logger.info(f"Metrics saved to {metrics_path}")
        
        return metrics_path
    
    def save_feature_importance(self) -> str:
        """
        Save feature importance to CSV.
        
        Returns:
            Path to feature importance file
        """
        logger.info("Saving feature importance...")
        
        output_dir = config.get('output_dir')
        importance_path = os.path.join(output_dir, 'feature_importance.csv')
        
        # Get feature importance
        importance = self.model.get_feature_importance(type='PredictionValuesChange')
        
        # Create DataFrame
        importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        importance_df.to_csv(importance_path, index=False)
        
        logger.info(f"Feature importance saved to {importance_path}")
        logger.info(f"Top 10 features:\n{importance_df.head(10)}")
        
        return importance_path
    
    def save_predictions(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> str:
        """
        Save test predictions to CSV.
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Path to predictions file
        """
        logger.info("Saving predictions...")
        
        output_dir = config.get('output_dir')
        predictions_path = os.path.join(output_dir, 'predictions.csv')
        
        # Make predictions
        test_pool = Pool(data=X_test, cat_features=self.categorical_features)
        y_pred = self.model.predict(test_pool)
        
        # Create DataFrame
        predictions_df = pd.DataFrame({
            'actual': y_test.values,
            'predicted': y_pred,
            'residual': y_test.values - y_pred,
            'absolute_error': np.abs(y_test.values - y_pred)
        })
        
        predictions_df.to_csv(predictions_path, index=False)
        
        logger.info(f"Predictions saved to {predictions_path}")
        
        return predictions_path
    
    def save_model_config(self) -> str:
        """
        Save model configuration to JSON.
        
        Returns:
            Path to config file
        """
        logger.info("Saving model configuration...")
        
        output_dir = config.get('output_dir')
        config_path = os.path.join(output_dir, 'model_config.json')
        
        model_config = {
            'model_params': {
                'iterations': config.get('iterations'),
                'learning_rate': config.get('learning_rate'),
                'depth': config.get('depth'),
                'l2_leaf_reg': config.get('l2_leaf_reg'),
                'loss_function': config.get('loss_function'),
                'eval_metric': config.get('eval_metric'),
                'random_seed': config.get('random_seed'),
                'early_stopping_rounds': config.get('early_stopping_rounds')
            },
            'feature_names': self.feature_names,
            'categorical_features': self.categorical_features,
            'target_column': config.get('target_column'),
            'training_date': datetime.now().isoformat(),
            'best_iteration': int(self.model.best_iteration_) if self.model else None
        }
        
        with open(config_path, 'w') as f:
            json.dump(model_config, f, indent=2)
        
        logger.info(f"Model config saved to {config_path}")
        
        return config_path
    
    def generate_plots(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> dict:
        """
        Generate evaluation plots.
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Dictionary of plot file paths
        """
        logger.info("Generating evaluation plots...")
        
        plots_dir = config.get('plots_dir')
        plot_paths = {}
        
        # Make predictions
        test_pool = Pool(data=X_test, cat_features=self.categorical_features)
        y_pred = self.model.predict(test_pool)
        
        # Actual vs Predicted plot
        if config.get('plot_actual_vs_predicted', True):
            plt.figure(figsize=(10, 6))
            plt.scatter(y_test, y_pred, alpha=0.5, s=1)
            plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
            plt.xlabel('Actual Passenger Count')
            plt.ylabel('Predicted Passenger Count')
            plt.title('Actual vs Predicted Passenger Count')
            plt.grid(True, alpha=0.3)
            
            actual_pred_path = os.path.join(plots_dir, 'actual_vs_predicted.png')
            plt.savefig(actual_pred_path, dpi=150, bbox_inches='tight')
            plt.close()
            plot_paths['actual_vs_predicted'] = actual_pred_path
            logger.info(f"Saved actual vs predicted plot to {actual_pred_path}")
        
        # Residual distribution plot
        if config.get('plot_residuals', True):
            residuals = y_test - y_pred
            
            plt.figure(figsize=(10, 6))
            plt.hist(residuals, bins=50, edgecolor='black', alpha=0.7)
            plt.axvline(x=0, color='r', linestyle='--', lw=2)
            plt.xlabel('Residual (Actual - Predicted)')
            plt.ylabel('Frequency')
            plt.title('Residual Distribution')
            plt.grid(True, alpha=0.3)
            
            residuals_path = os.path.join(plots_dir, 'residual_distribution.png')
            plt.savefig(residuals_path, dpi=150, bbox_inches='tight')
            plt.close()
            plot_paths['residual_distribution'] = residuals_path
            logger.info(f"Saved residual distribution plot to {residuals_path}")
        
        # Feature importance plot
        if config.get('plot_feature_importance', True):
            importance = self.model.get_feature_importance(type='PredictionValuesChange')
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False).head(20)
            
            plt.figure(figsize=(12, 8))
            plt.barh(importance_df['feature'], importance_df['importance'])
            plt.xlabel('Importance')
            plt.ylabel('Feature')
            plt.title('Top 20 Feature Importance')
            plt.gca().invert_yaxis()
            plt.grid(True, alpha=0.3, axis='x')
            
            importance_plot_path = os.path.join(plots_dir, 'feature_importance.png')
            plt.savefig(importance_plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            plot_paths['feature_importance'] = importance_plot_path
            logger.info(f"Saved feature importance plot to {importance_plot_path}")
        
        return plot_paths
    
    def train_and_evaluate(self) -> dict:
        """
        Complete training pipeline: load data, train, evaluate, save outputs.
        
        Returns:
            Dictionary containing all output paths and metrics
        """
        logger.info("=" * 80)
        logger.info("Starting CatBoost Training Pipeline")
        logger.info("=" * 80)
        
        try:
            # Load and split data
            X_train, X_val, X_test, y_train, y_val, y_test = self.load_and_split_data()
            
            # Train model
            self.train_model(X_train, y_train, X_val, y_val)
            
            # Evaluate model
            metrics = self.evaluate_model(X_test, y_test)
            
            # Save outputs
            model_path = self.save_model()
            metrics_path = self.save_metrics()
            importance_path = self.save_feature_importance()
            predictions_path = self.save_predictions(X_test, y_test)
            config_path = self.save_model_config()
            plot_paths = self.generate_plots(X_test, y_test)
            
            # Summary
            logger.info("=" * 80)
            logger.info("Training Pipeline Completed Successfully")
            logger.info("=" * 80)
            logger.info(f"Model saved to: {model_path}")
            logger.info(f"Metrics saved to: {metrics_path}")
            logger.info(f"Feature importance saved to: {importance_path}")
            logger.info(f"Predictions saved to: {predictions_path}")
            logger.info(f"Model config saved to: {config_path}")
            logger.info(f"Plots saved to: {list(plot_paths.values())}")
            logger.info(f"\nFinal Metrics: RMSE={metrics['RMSE']:.4f}, MAE={metrics['MAE']:.4f}, R2={metrics['R2']:.4f}")
            
            return {
                'model_path': model_path,
                'metrics_path': metrics_path,
                'importance_path': importance_path,
                'predictions_path': predictions_path,
                'config_path': config_path,
                'plot_paths': plot_paths,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Training pipeline failed: {e}", exc_info=True)
            raise


def main():
    """Main entry point for training."""
    trainer = CatBoostTrainer()
    results = trainer.train_and_evaluate()
    return results


if __name__ == "__main__":
    main()
