// Terms of service stub — linked from `/register`. Honest placeholder
// until legal-reviewed text lands. Contact path is real.

import Link from "next/link";

import { PublicHeader } from "@/components/layout/PublicHeader";

export default function TermsPage() {
  return (
    <>
      <PublicHeader />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 prose prose-sm dark:prose-invert">
        <h1>Условия использования</h1>

        <p className="text-muted-foreground">
          Регистрируясь в ORGON, вы соглашаетесь с этими условиями.
          ORGON — B2B custodial wallet platform, оператор ОсОО «АСИСТЕМ»
          (КР, Бишкек). Регулируется законодательством Кыргызской
          Республики, в частности — законом о виртуальных активах,
          требованиями Финнадзора КР и Национального банка КР.
        </p>

        <h2>Кто может использовать ORGON</h2>
        <ul>
          <li>
            Юридические лица с лицензией оператора обмена ВА, оператора
            торговли ВА, или кастодиана (ст. Закона КР о ВА).
          </li>
          <li>
            Банки и финтех-компании КР, КЗ, РФ с соответствующим
            разрешением своего регулятора.
          </li>
          <li>
            Внутренние интеграции ОсОО «АСИСТЕМ» — для собственных
            продуктов экосистемы.
          </li>
        </ul>
        <p>
          Использование физическими лицами напрямую (без юридического
          лица-оператора) не предусмотрено — обращайтесь к
          лицензированному оператору, использующему ORGON под капотом.
        </p>

        <h2>Что вы обязаны соблюдать</h2>
        <ul>
          <li>
            <strong>AML / KYC</strong> — ORGON предоставляет
            инструменты (rule engine, SAR pipeline, KYC модули), но
            ответственность за compliance несёт оператор согласно своей
            лицензии.
          </li>
          <li>
            <strong>Безопасность ключей</strong> — `okl_*` / `oksl_*`
            ключи API хранятся у оператора. Утечка ключа = ваша
            ответственность; ротация бесплатна.
          </li>
          <li>
            <strong>SLA-fair-use</strong> — лимиты тарифа (см.{" "}
            <Link href="/pricing" className="text-primary hover:underline">
              /pricing
            </Link>
            ) — мягкие; превышение приводит к временному 429, а не к
            мгновенной блокировке.
          </li>
          <li>
            <strong>Запрещённые операции</strong> — отмывание, санкционные
            переводы, terror-financing. Эти операции автоматически
            блокируются AML-движком и подлежат отчётности в Финнадзор
            КР.
          </li>
        </ul>

        <h2>Что обязуется ORGON</h2>
        <ul>
          <li>
            Custody-уровневая безопасность ключей (multi-sig через
            Safina, HSM-ready signer abstraction).
          </li>
          <li>
            Прозрачный audit log с request-id трассировкой.
          </li>
          <li>
            Регуляторные отчёты (SAR/CTR/HRC под Финнадзор КР).
          </li>
          <li>
            Webhook доставка с retry (до 6 попыток, до 34 часов).
          </li>
        </ul>

        <h2>Ограничение ответственности</h2>
        <p>
          ORGON не несёт ответственности за: упущенную выгоду от
          задержек блокчейн-сети, действия пользователей оператора
          (включая ошибочные адреса), регуляторные штрафы, наступившие
          по вине оператора (например, неподача SAR в срок при
          корректно сформированном файле в `sar_submissions`).
        </p>

        <h2>Расторжение</h2>
        <p>
          Оператор может отключиться в любой момент. ORGON может
          приостановить доступ при подтверждённом нарушении (приоритет
          — уведомление, потом suspend; немедленный suspend только при
          явной угрозе средствам).
        </p>

        <h2>Контакт</h2>
        <p>
          По вопросам условий пишите на{" "}
          <a
            href="mailto:support@orgon.asystem.kg"
            className="text-primary hover:underline"
          >
            support@orgon.asystem.kg
          </a>
          . Полная редакция, согласованная с юристами, появится здесь
          после прохождения проверки — предварительный текст выше
          отражает фактический режим работы платформы.
        </p>

        <p className="text-xs text-muted-foreground mt-8">
          См. также:{" "}
          <Link href="/privacy" className="text-primary hover:underline">
            Политика конфиденциальности
          </Link>{" "}
          ·{" "}
          <Link href="/pricing" className="text-primary hover:underline">
            Тарифы
          </Link>
        </p>
      </main>
    </>
  );
}
