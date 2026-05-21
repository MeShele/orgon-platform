'use client';
import { useState, useCallback } from 'react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/ui/Card';
import { Icon } from '@/lib/icons';
import { pageLayout, buttonStyles } from '@/lib/page-layout';
import { DocumentViewer } from '@/components/DocumentViewer';

const SUPPORTED_TYPES = ['docx', 'xlsx', 'pptx', 'pdf', 'doc', 'xls', 'ppt', 'odt', 'ods', 'csv', 'txt', 'rtf'];

export default function DocumentsPage() {
  const [fileUrl, setFileUrl] = useState('');
  const [fileName, setFileName] = useState('');
  const [fileType, setFileType] = useState('docx');
  const [token, setToken] = useState('');
  const [showViewer, setShowViewer] = useState(false);
  const [editable, setEditable] = useState(false);
  const [loading, setLoading] = useState(false);

  const openDocument = useCallback(async () => {
    if (!fileUrl || !fileName) return;
    setLoading(true);
    try {
      const res = await fetch('/api/documents/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_url: fileUrl,
          file_name: fileName,
          file_type: fileType,
          mode: editable ? 'edit' : 'view',
        }),
      });
      const data = await res.json();
      setToken(data.token);
      setShowViewer(true);
    } catch {
      setShowViewer(true);
    } finally {
      setLoading(false);
    }
  }, [fileUrl, fileName, fileType, editable]);

  const getFileIcon = (type: string) => {
    const icons: Record<string, string> = {
      docx: 'solar:document-text-bold',
      doc: 'solar:document-text-bold',
      xlsx: 'solar:chart-square-bold',
      xls: 'solar:chart-square-bold',
      pptx: 'solar:presentation-graph-bold',
      ppt: 'solar:presentation-graph-bold',
      pdf: 'solar:file-check-bold',
      csv: 'solar:database-bold',
      txt: 'solar:document-bold',
    };
    return icons[type] || 'solar:document-bold';
  };

  return (
    <>
      <Header title="Документы" />
      <div className={pageLayout.container}>
        {/* Roadmap banner — sidebar marks this route as `roadmap: true`
            (`sidebar-nav.ts`); the page is intentionally a viewer-only
            utility today. Document library + upload + sharing flows
            are scoped for Sprint 8. Removing this banner is gated on
            that ship — until then, set honest expectations up-front so
            the user doesn't dig for a "my documents" list that
            doesn't exist yet. */}
        <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/5 p-4 text-[13px]">
          <Icon icon="solar:info-circle-bold" className="text-warning mt-0.5 shrink-0 text-base" />
          <div className="text-foreground">
            <div className="font-medium">Документы — превью по URL</div>
            <div className="mt-1 text-muted-foreground">
              Полноценное хранилище (загрузка, история версий, обмен ссылками между пользователями) — в разработке.
              Сейчас доступен только предпросмотр документа по прямой ссылке в OnlyOffice.
            </div>
          </div>
        </div>

        {/* Открыть документ */}
        <Card>
          <div className="p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
              <Icon icon="solar:document-add-linear" className="text-primary" />
              Открыть документ
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">URL документа</label>
                <input
                  type="url"
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  placeholder="https://example.com/document.docx"
                  className="w-full px-4 py-2 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 border-border bg-card text-foreground"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Имя файла</label>
                <input
                  type="text"
                  value={fileName}
                  onChange={(e) => setFileName(e.target.value)}
                  placeholder="document.docx"
                  className="w-full px-4 py-2 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 border-border bg-card text-foreground"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Тип файла</label>
                <select
                  value={fileType}
                  onChange={(e) => setFileType(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary/30 border-border bg-card text-foreground"
                >
                  {SUPPORTED_TYPES.map((t) => (
                    <option key={t} value={t}>{t.toUpperCase()}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end gap-4">
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    checked={editable}
                    onChange={(e) => setEditable(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary/30"
                  />
                  Режим редактирования
                </label>
                <button
                  onClick={openDocument}
                  disabled={!fileUrl || !fileName || loading}
                  className={`${buttonStyles.primary || 'px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:opacity-90'} flex items-center gap-2 disabled:opacity-50`}
                >
                  {loading ? (
                    <Icon icon="solar:refresh-linear" className="animate-spin" />
                  ) : (
                    <Icon icon="solar:eye-linear" />
                  )}
                  Открыть
                </button>
              </div>
            </div>
          </div>
        </Card>

        {/* Просмотрщик */}
        {showViewer && (
          <Card>
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Icon icon={getFileIcon(fileType)} className="text-primary" />
                <span className="font-medium text-foreground">{fileName}</span>
                {editable && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-warning/10 text-warning">
                    Редактирование
                  </span>
                )}
              </div>
              <button
                onClick={() => setShowViewer(false)}
                className="text-muted-foreground hover:text-destructive transition-colors"
              >
                <Icon icon="solar:close-circle-linear" className="text-xl" />
              </button>
            </div>
            <DocumentViewer
              fileUrl={fileUrl}
              fileName={fileName}
              fileType={fileType}
              editable={editable}
              token={token}
            />
          </Card>
        )}
      </div>
    </>
  );
}
