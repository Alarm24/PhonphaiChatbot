import { Badge } from './ui/badge';

interface QuickReplyChipsProps {
  onSelect: (text: string) => void;
}

const quickReplies = [
  'How to report a flood?',
  'Forgot Password',
  'Where is the nearest shelter?',
  'Contact Official',
  'Emergency Hotline',
  'Safety Guidelines',
];

export function QuickReplyChips({ onSelect }: QuickReplyChipsProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
      {quickReplies.map((reply) => (
        <Badge
          key={reply}
          variant="outline"
          className="cursor-pointer whitespace-nowrap px-4 py-2 border-[#D32F2F] text-[#D32F2F] hover:bg-[#D32F2F] hover:text-white transition-colors"
          onClick={() => onSelect(reply)}
        >
          {reply}
        </Badge>
      ))}
    </div>
  );
}
