import React, { useState } from 'react';
import { Plus, X } from 'lucide-react';

const FloatingActionButton = ({ actions }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-4 right-4 flex flex-col-reverse items-end">
      {isOpen && (
        <div className="mb-2 space-y-2">
          {actions.map((action, index) => (
            <button
              key={index}
              onClick={() => {
                action.onClick();
                setIsOpen(false);
              }}
              className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-500 text-white shadow-lg hover:bg-blue-600 transition-colors duration-200"
            >
              {action.icon}
            </button>
          ))}
        </div>
      )}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-center w-16 h-16 rounded-full bg-blue-500 text-white shadow-lg hover:bg-blue-600 transition-colors duration-200"
      >
        {isOpen ? <X size={24} /> : <Plus size={24} />}
      </button>
    </div>
  );
};

export default FloatingActionButton;