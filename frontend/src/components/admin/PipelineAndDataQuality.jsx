import React from 'react';
import DataQuality from './DataQuality';
import PipelineMonitor from './PipelineMonitor';

export default function PipelineAndDataQuality() {
  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <DataQuality />
      <PipelineMonitor />
    </div>
  );
}
