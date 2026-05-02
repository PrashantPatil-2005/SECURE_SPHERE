import React from 'react';
import { 
  Shield, 
  Terminal, 
  Target, 
  AlertCircle, 
  CheckCircle2, 
  Fingerprint, 
  Zap,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function AINarrative({ narrative }) {
  if (!narrative) return null;

  let data = null;
  try {
    // If it's already an object, use it; otherwise parse it.
    data = typeof narrative === 'string' ? JSON.parse(narrative) : narrative;
  } catch (e) {
    // Fallback if it's not valid JSON
    return (
      <div className="p-4 bg-base-950/50 border border-base-800 rounded-lg">
        <p className="text-[11px] text-base-400 italic leading-relaxed whitespace-pre-wrap">
          {typeof narrative === 'object' ? (narrative.level || JSON.stringify(narrative)) : String(narrative)}
        </p>
      </div>
    );
  }

  const Section = ({ title, icon: Icon, children, colorClass = "text-base-100" }) => (
    <div className="mb-4 last:mb-0">
      <div className="flex items-center gap-2 mb-1.5">
        <Icon className={cn("w-3.5 h-3.5", colorClass)} />
        <h4 className="text-[10px] uppercase tracking-wider font-bold text-base-500">
          {title}
        </h4>
      </div>
      <div className="pl-5 border-l border-base-800/50 ml-1.5">
        {children}
      </div>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-top-1 duration-500">
      {/* Executive Summary - Highlighted */}
      <div className="relative p-4 bg-accent/5 border border-accent/20 rounded-xl overflow-hidden group">
        <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
          <Shield className="w-12 h-12 text-accent" />
        </div>
        <Section title="Executive Summary" icon={Shield} colorClass="text-accent">
          <p className="text-xs text-base-100 leading-relaxed font-medium">
            {data.executive_summary}
          </p>
        </Section>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-6">
          {/* Technical Breakdown */}
          <Section title="Technical Analysis" icon={Terminal} colorClass="text-blue-400">
            <p className="text-[11px] text-base-300 leading-relaxed whitespace-pre-wrap">
              {data.technical_breakdown}
            </p>
          </Section>

          {/* Attacker Intent */}
          {data.attacker_intent && (
            <Section title="Attacker Intent" icon={Target} colorClass="text-red-400">
              <p className="text-[11px] text-base-400 leading-relaxed italic">
                {data.attacker_intent}
              </p>
            </Section>
          )}
        </div>

        <div className="space-y-6">
          {/* Attack Lifecycle */}
          {data.attack_lifecycle && (
            <Section title="Attack Lifecycle" icon={Zap} colorClass="text-amber-400">
              <div className="inline-flex px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-[10px] font-mono text-amber-300 uppercase font-bold">
                {data.attack_lifecycle}
              </div>
            </Section>
          )}

          {/* MITRE Mapping */}
          {data.mitre_mapping && data.mitre_mapping.length > 0 && (
            <Section title="MITRE ATT&CK Mapping" icon={Target} colorClass="text-base-100">
              <div className="space-y-2">
                {data.mitre_mapping.map((m, i) => (
                  <div key={i} className="p-2 rounded bg-base-950 border border-base-800">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono font-bold text-accent">{m.technique}</span>
                      <span className="text-[10px] font-bold text-base-200">{m.name}</span>
                    </div>
                    <p className="text-[10px] text-base-500 leading-tight">{m.description}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Blast Radius */}
          {data.blast_radius && (
            <Section title="Blast Radius" icon={AlertCircle} colorClass="text-orange-400">
              <p className="text-[11px] text-base-400 leading-relaxed">
                {data.blast_radius}
              </p>
            </Section>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        {/* Recommended Actions */}
        {data.recommended_actions && data.recommended_actions.length > 0 && (
          <Section title="Recommended Actions" icon={CheckCircle2} colorClass="text-emerald-400">
            <div className="space-y-2">
              {data.recommended_actions.map((ra, i) => (
                <div key={i} className="flex gap-2">
                  <div className={cn(
                    "w-1 h-auto rounded-full shrink-0",
                    ra.urgency === 'immediate' ? "bg-red-500" : ra.urgency === 'short-term' ? "bg-amber-500" : "bg-emerald-500"
                  )} />
                  <div>
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className={cn(
                        "text-[9px] uppercase font-bold px-1 rounded",
                        ra.urgency === 'immediate' ? "bg-red-500/20 text-red-400" : ra.urgency === 'short-term' ? "bg-amber-500/20 text-amber-400" : "bg-emerald-500/20 text-emerald-400"
                      )}>
                        {ra.urgency}
                      </span>
                      <span className="text-[11px] font-semibold text-base-200">{ra.action}</span>
                    </div>
                    <p className="text-[10px] text-base-500 italic">{ra.reasoning}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* Forensic Footprint */}
        {data.forensic_footprint && (
          <Section title="Forensic Footprint" icon={Fingerprint} colorClass="text-purple-400">
            <div className="p-2 rounded bg-base-950 border border-base-800 font-mono text-[10px] text-purple-300 whitespace-pre-wrap">
              {data.forensic_footprint}
            </div>
          </Section>
        )}
      </div>

      {/* Confidence Score */}
      {data.confidence && (
        <div className="mt-4 flex items-center justify-between p-2 rounded-lg bg-base-950/80 border border-base-800">
          <div className="flex items-center gap-2">
            <div className="relative w-8 h-8 flex items-center justify-center">
              <svg className="w-8 h-8 transform -rotate-90">
                <circle
                  cx="16" cy="16" r="14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-base-800"
                />
                <circle
                  cx="16" cy="16" r="14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeDasharray={88}
                  strokeDashoffset={88 - (88 * data.confidence.score) / 100}
                  className="text-accent"
                />
              </svg>
              <span className="absolute text-[8px] font-bold text-accent">{data.confidence.score}%</span>
            </div>
            <div>
              <div className="text-[10px] font-bold text-base-200">AI Confidence Score</div>
              <p className="text-[9px] text-base-500 max-w-md truncate" title={data.confidence.statement}>
                {data.confidence.statement}
              </p>
            </div>
          </div>
          {data.confidence.evidence && (
             <div className="flex -space-x-2">
                {data.confidence.evidence.slice(0, 3).map((ev, i) => (
                  <div key={i} title={ev} className="w-5 h-5 rounded-full bg-base-800 border border-base-950 flex items-center justify-center text-[8px] font-mono text-base-400">
                    {i+1}
                  </div>
                ))}
             </div>
          )}
        </div>
      )}
    </div>
  );
}
