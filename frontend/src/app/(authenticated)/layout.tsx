import { AppShell } from '../AppShell';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { WebSocketProvider } from '@/contexts/WebSocketContext';

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <WebSocketProvider><AppShell><ErrorBoundary>{children}</ErrorBoundary></AppShell></WebSocketProvider>;
}
