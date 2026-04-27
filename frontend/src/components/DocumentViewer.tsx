'use client';
import { useEffect, useRef, useState } from 'react';

interface DocumentViewerProps {
  fileUrl: string;
  fileName: string;
  fileType: string;
  editable?: boolean;
  token?: string;
}

export function DocumentViewer({ fileUrl, fileName, fileType, editable = false, token }: DocumentViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const editorRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const script = document.createElement('script');
    script.src = 'https://office.asystem.ai/web-apps/apps/api/documents/api.js';
    script.onload = () => {
      try {
        editorRef.current = new (window as any).DocsAPI.DocEditor('onlyoffice-editor', {
          document: {
            fileType,
            title: fileName,
            url: fileUrl,
            key: `${fileName}_${Date.now()}`,
          },
          editorConfig: {
            mode: editable ? 'edit' : 'view',
            lang: 'ru',
            callbackUrl: editable ? `${window.location.origin}/api/documents/callback` : undefined,
          },
          documentType: getDocType(fileType),
          token: token || undefined,
          events: {
            onReady: () => setLoading(false),
            onError: (e: any) => setError(e?.data || 'Editor error'),
          },
        });
      } catch (e: any) {
        setError(e.message);
        setLoading(false);
      }
    };
    script.onerror = () => {
      setError('Failed to load OnlyOffice editor');
      setLoading(false);
    };
    document.head.appendChild(script);

    return () => {
      if (editorRef.current?.destroyEditor) editorRef.current.destroyEditor();
      try { document.head.removeChild(script); } catch {}
    };
  }, [fileUrl, fileName, fileType, editable, token]);

  return (
    <div className="relative">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 z-10">
          <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
        </div>
      )}
      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg mb-2">
          {error}
        </div>
      )}
      <div id="onlyoffice-editor" ref={containerRef} style={{ height: '600px' }} />
    </div>
  );
}

function getDocType(ext: string): string {
  if (['doc', 'docx', 'odt', 'txt', 'pdf', 'rtf'].includes(ext)) return 'word';
  if (['xls', 'xlsx', 'ods', 'csv'].includes(ext)) return 'cell';
  if (['ppt', 'pptx', 'odp'].includes(ext)) return 'slide';
  return 'word';
}
