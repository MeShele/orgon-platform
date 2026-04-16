"use client";

import { Header } from "@/components/layout/Header";
import { CreateWalletForm } from "@/components/wallets/CreateWalletForm";

export default function NewWalletPage() {
  return (
    <>
      <Header title="Create Wallet" />
      <div className="p-4 sm:p-6 lg:p-8">
        <CreateWalletForm />
      </div>
    </>
  );
}
