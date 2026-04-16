// Playwright script to check browser console errors on orgon.asystem.ai
const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  const consoleMessages = [];
  const errors = [];
  const failedRequests = [];

  // Listen to console messages
  page.on('console', (msg) => {
    consoleMessages.push({
      type: msg.type(),
      text: msg.text(),
    });
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  // Listen to failed requests
  page.on('requestfailed', (request) => {
    failedRequests.push({
      url: request.url(),
      failure: request.failure().errorText,
    });
  });

  // Listen to page errors
  page.on('pageerror', (error) => {
    errors.push(`Page Error: ${error.message}`);
  });

  try {
    console.log('🌐 Открытие https://orgon.asystem.ai ...');
    await page.goto('https://orgon.asystem.ai', {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    console.log('✅ Страница загружена\n');

    // Wait a bit for dynamic content
    await page.waitForTimeout(5000);

    // Check page title
    const title = await page.title();
    console.log(`📄 Заголовок страницы: ${title}\n`);

    // Get page URL (might be redirected)
    const currentURL = page.url();
    console.log(`🔗 Текущий URL: ${currentURL}\n`);

    // Check for specific errors
    console.log('═══════════════════════════════════════════════════════════');
    console.log('📊 Результаты проверки:');
    console.log('═══════════════════════════════════════════════════════════\n');

    console.log(`🟢 Консольных сообщений: ${consoleMessages.length}`);
    console.log(`🔴 Ошибок в консоли: ${errors.length}`);
    console.log(`❌ Неудачных запросов: ${failedRequests.length}\n`);

    if (errors.length > 0) {
      console.log('═══════════════════════════════════════════════════════════');
      console.log('🔴 ОШИБКИ В КОНСОЛИ:');
      console.log('═══════════════════════════════════════════════════════════');
      errors.forEach((err, i) => {
        console.log(`${i + 1}. ${err}`);
      });
      console.log('');
    }

    if (failedRequests.length > 0) {
      console.log('═══════════════════════════════════════════════════════════');
      console.log('❌ НЕУДАЧНЫЕ ЗАПРОСЫ:');
      console.log('═══════════════════════════════════════════════════════════');
      failedRequests.forEach((req, i) => {
        console.log(`${i + 1}. ${req.url}`);
        console.log(`   Причина: ${req.failure}\n`);
      });
    }

    // Check if specific elements are present
    console.log('═══════════════════════════════════════════════════════════');
    console.log('🔍 Проверка элементов страницы:');
    console.log('═══════════════════════════════════════════════════════════');

    const checks = [
      { selector: 'h1', name: 'Заголовок (h1)' },
      { selector: 'nav', name: 'Навигация' },
      { selector: 'main', name: 'Основной контент' },
      { selector: 'button', name: 'Кнопки' },
    ];

    for (const check of checks) {
      const element = await page.$(check.selector);
      console.log(`${element ? '✅' : '❌'} ${check.name}`);
    }

    console.log('\n');

    // Take screenshot
    const screenshotPath = 'orgon-screenshot.png';
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`📸 Скриншот сохранён: ${screenshotPath}\n`);

    // Summary
    console.log('═══════════════════════════════════════════════════════════');
    console.log('📋 ИТОГ:');
    console.log('═══════════════════════════════════════════════════════════');
    
    if (errors.length === 0 && failedRequests.length === 0) {
      console.log('✅ Критических ошибок не обнаружено!');
    } else {
      console.log('⚠️  Обнаружены проблемы:');
      if (errors.length > 0) {
        console.log(`   - ${errors.length} ошибок в консоли`);
      }
      if (failedRequests.length > 0) {
        console.log(`   - ${failedRequests.length} неудачных запросов`);
      }
    }
    console.log('═══════════════════════════════════════════════════════════\n');

  } catch (error) {
    console.error('❌ Ошибка при проверке:', error.message);
  } finally {
    await browser.close();
  }
})();
