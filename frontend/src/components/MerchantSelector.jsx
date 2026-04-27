function MerchantSelector({ merchants, selectedMerchant, onMerchantChange }) {
  return (
    <div className="card">
      <label htmlFor="merchant-select" className="block text-sm font-medium text-gray-700 mb-2">
        Select Merchant
      </label>
      <select
        id="merchant-select"
        value={selectedMerchant || ''}
        onChange={(e) => onMerchantChange(e.target.value)}
        className="input-field"
      >
        {merchants.map((merchant) => (
          <option key={merchant.id} value={merchant.id}>
            {merchant.name} ({merchant.email})
          </option>
        ))}
      </select>
    </div>
  );
}

export default MerchantSelector;
