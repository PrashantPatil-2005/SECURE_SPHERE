import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export default function MitrePanel() {
  return (
    <Card className="overflow-hidden bg-base-900 border-white/[0.05]">
      <CardHeader>
        <CardTitle className="text-base-100 flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
          MITRE ATT&CK Matrix
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center py-6 text-base-500 text-xs">
          <p>Techniques will be mapped here as incidents develop.</p>
        </div>
      </CardContent>
    </Card>
  );
}
