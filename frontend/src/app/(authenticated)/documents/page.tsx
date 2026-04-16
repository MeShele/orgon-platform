'use client';
import { useState, useCallback } from 'react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
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
  const [recentDocs] = useState([
    { name: 'Политика безопасности.docx', type: 'docx', date: '2026-02-15' },
    { name: 'Отчёт Q4.xlsx', type: 'xlsx', date: '2026-02-10' },
    { name: 'Договор поставки.pdf', type: 'pdf', date: '2026-02-08' },
  ]);

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
        
        {/* Открыть документ */}
        <Card>
          <div className="p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Icon icon="solar:document-add-linear" className="text-indigo-500" />
              Открыть документ
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">URL документа</label>
                <input
                  type="url"
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  placeholder="https://example.com/document.docx"
                  className="w-full px-4 py-2 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Имя файла</label>
                <input
                  type="text"
                  value={fileName}
                  onChange={(e) => setFileName(e.target.value)}
                  placeholder="document.docx"
                  className="w-full px-4 py-2 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Тип файла</label>
                <select
                  value={fileType}
                  onChange={(e) => setFileType(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  {SUPPORTED_TYPES.map((t) => (
                    <option key={t} value={t}>{t.toUpperCase()}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end gap-4">
                <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={editable}
                    onChange={(e) => setEditable(e.target.checked)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Режим редактирования
                </label>
                <button
                  onClick={openDocument}
                  disabled={!fileUrl || !fileName || loading}
                  className={`${buttonStyles.primary || 'px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700'} flex items-center gap-2 disabled:opacity-50`}
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

        {/* Недавние документы */}
        <Card>
          <div className="p-4 sm:p-6">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Icon icon="solar:history-linear" className="text-slate-500" />
              Недавние документы
            </h2>
            <div className="space-y-2">
              {recentDocs.map((doc, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <Icon icon={getFileIcon(doc.type)} className="text-xl text-indigo-500" />
                    <div>
                      <p className="text-sm font-medium text-slate-900 dark:text-white">{doc.name}</p>
                      <p className="text-xs text-slate-500">{doc.date}</p>
                    </div>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 uppercase font-medium">
                    {doc.type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Просмотрщик */}
        {showViewer && (
          <Card>
            <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-2">
                <Icon icon={getFileIcon(fileType)} className="text-indigo-500" />
                <span className="font-medium text-slate-900 dark:text-white">{fileName}</span>
                {editable && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                    Редактирование
                  </span>
                )}
              </div>
              <button
                onClick={() => setShowViewer(false)}
                className="text-slate-400 hover:text-red-500 transition-colors"
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
