"use client";

import { Header } from "@/components/layout/Header";
import { SendForm } from "@/components/transactions/SendForm";

export default function NewTransactionPage() {
  return (
    <>
      <Header title="Новая транзакция" />
      <div className="p-4 sm:p-6 lg:p-8">
        <SendForm />
      </div>
    </>
  );
}
