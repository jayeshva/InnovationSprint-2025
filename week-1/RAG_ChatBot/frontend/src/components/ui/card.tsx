import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ 
  children, 
  className = '', 
  ...props 
}) => {
  return (
    <div 
      className={`rounded-lg border bg-white shadow-sm ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardContent: React.FC<CardProps> = ({ 
  children, 
  className = '', 
  ...props 
}) => {
  return (
    <div 
      className={`p-6 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};
