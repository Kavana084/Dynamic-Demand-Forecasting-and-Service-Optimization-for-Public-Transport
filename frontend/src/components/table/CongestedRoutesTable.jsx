import clsx from 'clsx';

export default function CongestedRoutesTable({ data }) {
  if (!data || data.length === 0) return null;

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-slate-100">
            <th className="py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Route</th>
            <th className="py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Current Load</th>
            <th className="py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Predicted Load (2 PM)</th>
            <th className="py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {data.map((row, idx) => (
            <tr key={idx} className="hover:bg-slate-50 transition-colors">
              <td className="py-3 px-4 text-sm font-medium text-slate-800">{row.route}</td>
              <td className="py-3 px-4 text-sm text-slate-600">{typeof row.currentLoad === 'number' ? `${row.currentLoad}%` : row.currentLoad}</td>
              <td className="py-3 px-4 text-sm text-slate-600">{row.predictedLoad}%</td>
              <td className="py-3 px-4">
                <span className={clsx(
                  "text-xs font-medium px-2.5 py-1 rounded-full",
                  row.status === 'High' ? "bg-red-50 text-red-600" : "bg-orange-50 text-orange-600"
                )}>
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
