// Privacy policy stub — linked from `/register`. Honest placeholder
// until legal-reviewed text lands. Contact path is real, not fake.

import Link from "next/link";

import { PublicHeader } from "@/components/layout/PublicHeader";

export default function PrivacyPage() {
  return (
    <>
      <PublicHeader />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 prose prose-sm dark:prose-invert">
        <h1>Политика конфиденциальности</h1>

        <p className="text-muted-foreground">
          ОсОО «АСИСТЕМ» (Кыргызская Республика, г. Бишкек) обрабатывает
          персональные данные в рамках работы платформы ORGON в
          соответствии с Конституционным законом КР «О персональных
          данных», требованиями Финнадзора КР и правилами защиты данных
          лицензированных VA-операторов.
        </p>

        <h2>Какие данные мы обрабатываем</h2>
        <ul>
          <li>
            <strong>Учётные данные оператора</strong> — email, имя
            ответственного лица, название юридического лица, ИНН.
          </li>
          <li>
            <strong>KYC/KYB end-user данные</strong> — собираются и
            хранятся в сертифицированных провайдерах (Sumsub, ASystem
            KYC, Biometric Vision). ORGON хранит только статус
            верификации и `external_id`, документы не дублируются.
          </li>
          <li>
            <strong>Транзакционные метаданные</strong> — адреса
            кошельков, tx_hash, сумма, время. Эти данные обязаны
            сохраняться согласно требованиям Финнадзора КР (минимум 5
            лет).
          </li>
          <li>
            <strong>Технические данные</strong> — IP, user-agent,
            request_id. Используются только для аудита и расследования
            инцидентов.
          </li>
        </ul>

        <h2>Где данные хранятся</h2>
        <p>
          PostgreSQL 16 на серверах ОсОО «АСИСТЕМ» в Кыргызстане.
          Шифрование секретов через pgcrypto (envelope-encryption с
          `MERCHANT_KEY_MASTER`). Резервные копии — gzip + опциональное
          S3-зеркалирование (если включено в настройках развёртывания).
          Подробнее в технической документации репозитория.
        </p>

        <h2>Кому передаются данные</h2>
        <p>
          Только трём категориям контрагентов:
        </p>
        <ul>
          <li>
            <strong>Финнадзор КР</strong> — по требованию (SAR, CTR,
            CDD-отчёты согласно закону 87/2018 и ПКМ 739/2025).
          </li>
          <li>
            <strong>Sumsub / Biometric Vision / Didit</strong> —
            KYC/KYB-провайдеры, выбранные оператором. Только если
            оператор активировал соответствующий модуль.
          </li>
          <li>
            <strong>Safina Pay</strong> — для multi-sig подписи
            on-chain транзакций. Передаются только данные транзакций,
            не PII.
          </li>
        </ul>

        <h2>Ваши права</h2>
        <p>
          У вас есть право запросить копию ваших данных, их исправление
          или удаление (с учётом регуляторных обязательств по хранению
          транзакционной истории).
        </p>

        <h2>Контакт</h2>
        <p>
          По вопросам обработки данных пишите на{" "}
          <a
            href="mailto:support@orgon.asystem.kg"
            className="text-primary hover:underline"
          >
            support@orgon.asystem.kg
          </a>
          . Полная редакция политики, согласованная с юристами, появится
          здесь после прохождения регуляторной проверки —
          предварительный текст выше отражает фактический режим работы
          платформы на сегодня.
        </p>

        <p className="text-xs text-muted-foreground mt-8">
          См. также: <Link href="/terms" className="text-primary hover:underline">Условия использования</Link>{" "}
          · <Link href="/pricing" className="text-primary hover:underline">Тарифы</Link>
        </p>
      </main>
    </>
  );
}
