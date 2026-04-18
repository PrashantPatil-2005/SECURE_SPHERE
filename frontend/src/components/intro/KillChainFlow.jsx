import { cn } from '@/lib/utils';
import { ArrowRight } from 'lucide-react';

const STEPS = [
  {
    stepKind: 'start',
    service: 'auth-service',
    stepLabel: 'Start',
    attack: 'Initial access — credential abuse and token replay against the identity plane.',
  },
  {
    stepKind: 'step',
    service: 'api-gateway',
    stepLabel: 'Step',
    attack: 'Ingress pivot — malicious requests forwarded into the workload mesh.',
  },
  {
    stepKind: 'step',
    service: 'api-server',
    stepLabel: 'Step',
    attack: 'Exploit chain continues against the business API tier and downstream contracts.',
  },
  {
    stepKind: 'end',
    service: 'payment-svc',
    stepLabel: 'End',
    attack: 'High-value target — fraud or data exfiltration as the operator’s objective.',
  },
];

function FlowNode({ stepKind, service, stepLabel, attack }) {
  const isStart = stepKind === 'start';
  const isEnd = stepKind === 'end';
  return (
    <div
      className={cn(
        'flex min-w-0 flex-col rounded-lg border bg-base-900/90 p-3',
        isStart && 'border-base-600 ring-1 ring-base-700/40',
        isEnd && 'border-base-700 ring-1 ring-base-800/50',
        !isStart && !isEnd && 'border-base-800'
      )}
    >
      <span
        className={cn(
          'mb-1 w-fit rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider',
          isStart && 'bg-base-800 text-base-200',
          isEnd && 'bg-base-800/80 text-base-300',
          !isStart && !isEnd && 'bg-base-800 text-base-500'
        )}
      >
        {stepLabel}
      </span>
      <div className="font-mono text-xs font-semibold text-base-200">{service}</div>
      <p className="mt-2 text-[11px] leading-snug text-base-500">{attack}</p>
    </div>
  );
}

function ArrowDivider() {
  return (
    <div className="flex justify-center py-1 lg:flex lg:items-center lg:justify-center lg:py-0" aria-hidden>
      <ArrowRight className="h-4 w-4 rotate-90 text-base-600 lg:rotate-0" />
    </div>
  );
}

/**
 * auth-service → api-gateway → api-server → payment-svc (grayscale path emphasis).
 */
export default function KillChainFlow() {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs font-medium uppercase tracking-wide text-base-500">Example attack path</p>
      <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch lg:gap-2">
        <FlowNode {...STEPS[0]} />
        <ArrowDivider />
        <FlowNode {...STEPS[1]} />
        <ArrowDivider />
        <FlowNode {...STEPS[2]} />
        <ArrowDivider />
        <FlowNode {...STEPS[3]} />
      </div>
    </div>
  );
}
