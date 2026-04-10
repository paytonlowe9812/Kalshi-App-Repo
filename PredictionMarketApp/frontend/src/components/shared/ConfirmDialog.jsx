import React from 'react';
import Modal from './Modal';

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = 'CONFIRM',
  message = 'Are you sure?',
  confirmText = 'CONFIRM',
  cancelText = 'CANCEL',
  danger = false,
}) {
  return (
    <Modal open={open} onClose={onClose} title={title} width="max-w-sm">
      <p className="text-sm text-terminal-amber font-mono mb-5">{message}</p>
      <div className="flex flex-col-reverse md:flex-row justify-end gap-2 md:gap-3">
        <button onClick={onClose} className="btn-secondary w-full md:w-auto">
          {cancelText}
        </button>
        <button
          onClick={() => {
            onConfirm();
            onClose();
          }}
          className={`${danger ? 'btn-danger' : 'btn-primary'} w-full md:w-auto`}
        >
          {confirmText}
        </button>
      </div>
    </Modal>
  );
}
