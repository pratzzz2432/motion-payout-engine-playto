import { useState, useEffect } from "react";
import { payoutAPI } from "../services/api";

function PayoutHistory({ merchantId }) {

  const [payouts, setPayouts] = useState([]);

  useEffect(() => {
    loadPayouts();
  }, [merchantId]);

  const loadPayouts = async () => {
    try {
      const data = await payoutAPI.getPayouts(
        merchantId
      );

      console.log("PAYOUT DATA:", data);

      setPayouts(
        data.payouts || []
      );

    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="card">
      <h2 className="text-xl font-bold mb-4">
        Payout History
      </h2>

      <button
        onClick={loadPayouts}
        className="mb-4 border px-3 py-1"
      >
        Refresh
      </button>

      {payouts.length === 0 && (
        <p>No payout history yet</p>
      )}

      {payouts.length > 0 && (
        <div>
          {payouts.map((p) => (
            <div
              key={p.id}
              style={{
                border:"1px solid gray",
                marginBottom:"12px",
                padding:"12px"
              }}
            >
              <p>ID: {p.id}</p>

              <p>
                Amount:
                ₹{p.amount_rupees}
              </p>

              <p>
                Status:
                {p.status}
              </p>

              <p>
                Bank:
                {p.bank_account_details.account_name}
              </p>

              <p>
                Created:
                {p.created_at}
              </p>

            </div>
          ))}
        </div>
      )}

    </div>
  );
}

export default PayoutHistory;