import { useState } from 'react';
import { payoutAPI } from '../services/api';

function PayoutForm({ merchant, onPayoutCreated }) {
  const [amount, setAmount] = useState('');
  const [selectedBankAccount, setSelectedBankAccount] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!amount || !selectedBankAccount) {
      setError('Please fill in all fields');
      return;
    }

    const amountRupees = parseFloat(amount);
    const amountPaise = Math.round(amountRupees * 100);

    if (amountPaise > merchant.available_balance.paise) {
      setError('Insufficient balance');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      await payoutAPI.createPayout(merchant.id, amountPaise, selectedBankAccount);

      setSuccess(`Payout of ₹${amountRupees.toFixed(2)} created successfully!`);
      setAmount('');
      onPayoutCreated();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create payout');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-gray-900 mb-4">Request Payout</h2>

      {/* Success Message */}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800 text-sm">{success}</p>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Amount Input */}
        <div className="mb-4">
          <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-2">
            Amount (₹)
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-500 sm:text-sm">₹</span>
            </div>
            <input
              type="number"
              id="amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              step="0.01"
              min="0.01"
              max={merchant.available_balance.rupees}
              placeholder="0.00"
              className="input-field pl-7"
              disabled={loading}
            />
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Available: ₹{merchant.available_balance.rupees.toFixed(2)}
          </p>
        </div>

        {/* Bank Account Selection */}
        <div className="mb-4">
          <label htmlFor="bank-account" className="block text-sm font-medium text-gray-700 mb-2">
            Bank Account
          </label>
          <select
            id="bank-account"
            value={selectedBankAccount}
            onChange={(e) => setSelectedBankAccount(e.target.value)}
            className="input-field"
            disabled={loading}
          >
            <option value="">Select a bank account</option>
            {merchant.bank_accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.account_name} - {account.ifsc_code}
              </option>
            ))}
          </select>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || !amount || !selectedBankAccount}
          className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </span>
          ) : (
            'Create Payout Request'
          )}
        </button>
      </form>

      {/* Info Box */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-blue-400 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">Payout Processing</p>
            <p className="text-xs">
              Payouts are processed automatically. 70% succeed, 20% fail, and 10% may require retry.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PayoutForm;
