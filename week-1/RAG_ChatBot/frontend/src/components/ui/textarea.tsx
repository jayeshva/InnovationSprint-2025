import React from 'react';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  minRows?: number;
  maxRows?: number;
}

export const Textarea: React.FC<TextareaProps> = ({ 
  className = '', 
  minRows = 3,
  maxRows = 8,
  ...props 
}) => {
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const adjustHeight = () => {
      textarea.style.height = 'auto';
      const lineHeight = parseInt(getComputedStyle(textarea).lineHeight);
      const paddingTop = parseInt(getComputedStyle(textarea).paddingTop);
      const paddingBottom = parseInt(getComputedStyle(textarea).paddingBottom);
      
      const minHeight = (minRows * lineHeight) + paddingTop + paddingBottom;
      const maxHeight = (maxRows * lineHeight) + paddingTop + paddingBottom;
      
      const newHeight = Math.min(Math.max(textarea.scrollHeight, minHeight), maxHeight);
      textarea.style.height = `${newHeight}px`;
    };

    textarea.addEventListener('input', adjustHeight);
    adjustHeight();

    return () => {
      textarea.removeEventListener('input', adjustHeight);
    };
  }, [minRows, maxRows]);

  return (
    <textarea 
      ref={textareaRef}
      className={`flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
};
