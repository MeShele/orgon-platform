'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from '@/hooks/useTranslations';
import { api } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { SafeIcon as Icon } from '@/components/SafeIcon';

interface TwoFAStatus {
  enabled: boolean;
  backup_codes_total: number;
  backup_codes_remaining: number;
}

export function TwoFactorAuth() {
  const t = useTranslations('settings.twofa');
  const tc = useTranslations('common');
  
  const [status, setStatus] = useState<TwoFAStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupStep, setSetupStep] = useState<'idle' | 'qr' | 'verify' | 'backup'>('idle');
  
  // Setup state
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [verificationCode, setVerificationCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const data = await api.getTwoFactorStatus();
      setStatus(data);
    } catch (err: any) {
      console.error('Failed to load 2FA status:', err);
    } finally {
      setLoading(false);
    }
  };

  const startSetup = async () => {
    setLoading(true);
    setError('');
    
    try {
      const data = await api.setupTwoFactor();
      setQrCode(data.qr_code);
      setSecret(data.secret);
      setBackupCodes(data.backup_codes);
      setSetupStep('qr');
    } catch (err: any) {
      setError(err.message || t('errors.setupFailed'));
    } finally {
      setLoading(false);
    }
  };

  const verifyAndEnable = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError(t('errors.invalidCode'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.enableTwoFactor(verificationCode);
      
      setSetupStep('backup');
      await loadStatus();
    } catch (err: any) {
      setError(err.message || t('errors.verificationFailed'));
    } finally {
      setLoading(false);
    }
  };

  const disable2FA = async () => {
    if (!disableCode || disableCode.length !== 6) {
      setError(t('errors.invalidCode'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.disableTwoFactor(disableCode);
      
      setSetupStep('idle');
      setDisableCode('');
      await loadStatus();
    } catch (err: any) {
      setError(err.message || t('errors.disableFailed'));
    } finally {
      setLoading(false);
    }
  };

  const regenerateBackupCodes = async () => {
    const code = prompt(t('prompts.enterCode'));
    if (!code) return;

    setLoading(true);
    try {
      const data = await api.regenerateBackupCodes(code);
      setBackupCodes(data.backup_codes);
      setSetupStep('backup');
    } catch (err: any) {
      setError(err.message || t('errors.regenerateFailed'));
    } finally {
      setLoading(false);
    }
  };

  const downloadBackupCodes = () => {
    const text = backupCodes.join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'orgon-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !status) {
    return (
      <Card>
        <div className="p-8 text-center">
          <Icon icon="solar:refresh-linear" className="text-4xl text-gray-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">{tc('loading')}</p>
        </div>
      </Card>
    );
  }

  // Setup flow
  if (setupStep !== 'idle') {
    return (
      <Card className="p-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">
          {t('setupTitle')}
        </h2>

        {/* Step 1: QR Code */}
        {setupStep === 'qr' && (
          <div className="space-y-6">
            <div className="text-center">
              <p className="text-gray-700 dark:text-gray-300 mb-4">
                {t('scanQR')}
              </p>
              
              {qrCode && (
                <img
                  src={qrCode}
                  alt="QR Code"
                  className="mx-auto border-4 border-gray-200 dark:border-gray-700 rounded-lg"
                />
              )}
              
              <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  {t('manualEntry')}
                </p>
                <code className="text-sm font-mono text-gray-900 dark:text-gray-100">
                  {secret}
                </code>
              </div>
            </div>

            <div>
              <Input
                type="text"
                label={t('verificationCode')}
                placeholder="000000"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                fullWidth
                helperText={t('enterCode')}
              />
            </div>

            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/20 rounded-lg text-sm text-red-700 dark:text-red-400">
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setSetupStep('idle');
                  setError('');
                }}
                fullWidth
              >
                {tc('cancel')}
              </Button>
              <Button
                variant="primary"
                onClick={verifyAndEnable}
                loading={loading}
                disabled={verificationCode.length !== 6}
                fullWidth
              >
                {t('verify')}
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: Backup Codes */}
        {setupStep === 'backup' && (
          <div className="space-y-6">
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-500/20 rounded-lg">
              <div className="flex gap-3">
                <Icon icon="solar:shield-warning-bold" className="text-yellow-600 dark:text-yellow-400 text-xl flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-1">
                    {t('saveBackupCodes')}
                  </h3>
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    {t('backupCodesWarning')}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              {backupCodes.map((code, idx) => (
                <div
                  key={idx}
                  className="font-mono text-sm text-gray-900 dark:text-gray-100 p-2 bg-white dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700"
                >
                  {code}
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={downloadBackupCodes}
                fullWidth
              >
                <Icon icon="solar:download-linear" className="mr-2" />
                {t('download')}
              </Button>
              <Button
                variant="primary"
                onClick={() => setSetupStep('idle')}
                fullWidth
              >
                {tc('done')}
              </Button>
            </div>
          </div>
        )}
      </Card>
    );
  }

  // Main view
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            {t('title')}
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            {t('description')}
          </p>
        </div>
        
        {status?.enabled && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-500/20 rounded-full">
            <Icon icon="solar:shield-check-bold" className="text-green-600 dark:text-green-400" />
            <span className="text-sm font-medium text-green-700 dark:text-green-300">
              {t('enabled')}
            </span>
          </div>
        )}
      </div>

      {!status?.enabled ? (
        <div className="space-y-4">
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-500/20 rounded-lg">
            <div className="flex gap-3">
              <Icon icon="solar:info-circle-bold" className="text-blue-600 dark:text-blue-400 text-xl flex-shrink-0" />
              <div className="text-sm text-blue-800 dark:text-blue-200">
                <p className="font-semibold mb-1">{t('whyEnable')}</p>
                <p>{t('securityBenefit')}</p>
              </div>
            </div>
          </div>

          <Button
            variant="primary"
            onClick={startSetup}
            loading={loading}
            fullWidth
          >
            <Icon icon="solar:shield-plus-bold" className="mr-2" />
            {t('enable')}
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                {t('backupCodesTotal')}
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {status.backup_codes_total}
              </p>
            </div>
            <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                {t('backupCodesRemaining')}
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {status.backup_codes_remaining}
              </p>
            </div>
          </div>

          <Button
            variant="secondary"
            onClick={regenerateBackupCodes}
            loading={loading}
            fullWidth
          >
            <Icon icon="solar:refresh-linear" className="mr-2" />
            {t('regenerateBackupCodes')}
          </Button>

          <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              {t('disable')}
            </h3>
            
            <div className="space-y-4">
              <Input
                type="text"
                label={t('verificationCode')}
                placeholder="000000"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6}
                fullWidth
                helperText={t('enterCodeToDisable')}
              />

              {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/20 rounded-lg text-sm text-red-700 dark:text-red-400">
                  {error}
                </div>
              )}

              <Button
                variant="danger"
                onClick={disable2FA}
                loading={loading}
                disabled={disableCode.length !== 6}
                fullWidth
              >
                <Icon icon="solar:shield-cross-bold" className="mr-2" />
                {t('disable')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
