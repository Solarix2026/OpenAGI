// Toast notification hook with react-hot-toast
import { Toaster, toast } from 'react-hot-toast';

interface ToastOptions {
  duration?: number;
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
}

export function useToast() {
  const addToast = (
    message: string,
    type: 'success' | 'error' | 'info' | 'warning' = 'info',
    options?: ToastOptions
  ) => {
    const config = {
      duration: options?.duration || 3000,
      position: options?.position || 'top-right',
      style: {
        background: 'var(--surface-2)',
        color: 'var(--text)',
        border: '1px solid var(--border)',
      },
      iconTheme: {
        primary: 'var(--blue)',
        secondary: 'var(--surface-1)',
      },
    };

    switch (type) {
      case 'success':
        toast.success(message, {
          ...config,
          iconTheme: { primary: 'var(--green)', secondary: 'var(--surface-1)' },
        });
        break;
      case 'error':
        toast.error(message, {
          ...config,
          iconTheme: { primary: 'var(--red)', secondary: 'var(--surface-1)' },
        });
        break;
      case 'warning':
        toast(message, {
          ...config,
          icon: '⚠️',
          iconTheme: { primary: 'var(--yellow)', secondary: 'var(--surface-1)' },
        });
        break;
      default:
        toast(message, config);
    }
  };

  const dismissToast = (id?: string) => {
    if (id) {
      toast.dismiss(id);
    } else {
      toast.dismiss();
    }
  };

  return {
    addToast,
    dismissToast,
    Toaster: () => <Toaster />,
  };
}

// Re-export Toaster for easy use
export { Toaster };
