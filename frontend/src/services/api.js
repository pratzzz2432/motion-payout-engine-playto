import axios from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Generate a UUID for idempotency
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export const merchantAPI = {
  // Get all merchants
  getMerchants: async () => {
    const response = await api.get('/merchants/');
    return response.data;
  },

  // Get merchant details with balances
  getMerchantDetails: async (merchantId) => {
    const response = await api.get(`/merchants/${merchantId}/`);
    return response.data;
  },
};

export const payoutAPI = {
  // Get all payouts for a merchant
  getPayouts: async (merchantId) => {
    const response = await api.get(`/merchants/${merchantId}/payouts/`);
    return response.data;
  },

  // Create a new payout request
  createPayout: async (merchantId, amountPaise, bankAccountId) => {
    const idempotencyKey = generateUUID();

    const response = await api.post(
      `/merchants/${merchantId}/payouts/`,
      {
        amount_paise: amountPaise,
        bank_account_id: bankAccountId,
      },
      {
        headers: {
          'Idempotency-Key': idempotencyKey,
        },
      }
    );
    return response.data;
  },
};

export const ledgerAPI = {
  // Get ledger entries for a merchant
  getLedgerEntries: async (merchantId) => {
    const response = await api.get(`/merchants/${merchantId}/ledger/`);
    return response.data;
  },
};

export default api;
