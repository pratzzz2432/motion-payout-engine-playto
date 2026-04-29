import { useState, useEffect } from 'react';
import { merchantAPI } from './services/api';
import MerchantSelector from './components/MerchantSelector';
import Dashboard from './components/Dashboard';
import PayoutForm from './components/PayoutForm';
import PayoutHistory from './components/PayoutHistory';
import LedgerEntries from './components/LedgerEntries';

function App() {
  const [merchants, setMerchants] = useState([]);
  const [selectedMerchant, setSelectedMerchant] = useState(null);
  const [merchantDetails, setMerchantDetails] = useState(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMerchants();
  }, []);

  useEffect(() => {
    if (selectedMerchant) {
      fetchMerchantDetails(selectedMerchant);
    }
  }, [selectedMerchant]);

  const fetchMerchants = async () => {
    try {
      setLoading(true);

      const data = await merchantAPI.getMerchants();

      setMerchants(data);

      if (data.length > 0) {
        setSelectedMerchant(data[0].id);
      }

    } catch (err) {
      setError(
        'Failed to fetch merchants. Make sure backend is running.'
      );

      console.error(err);

    } finally {
      setLoading(false);
    }
  };

  const fetchMerchantDetails = async (merchantId) => {
    try {
      setLoading(true);

      const data = await merchantAPI.getMerchantDetails(
        merchantId
      );

      setMerchantDetails(data);

    } catch (err) {
      setError(
        'Failed to fetch merchant details.'
      );

      console.error(err);

    } finally {
      setLoading(false);
    }
  };

  const handlePayoutCreated = () => {

    if (selectedMerchant) {
      fetchMerchantDetails(
        selectedMerchant
      );
    }

    // force PayoutHistory remount + refetch
    setHistoryRefreshKey(
      prev => prev + 1
    );
  };

  if (loading && !merchants.length) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">

          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto">
          </div>

          <p className="mt-4 text-gray-600">
            Loading...
          </p>

        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">

      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">

          <div className="flex items-center justify-between">

            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Playto Payout Engine
              </h1>

              <p className="text-sm text-gray-500 mt-1">
                Cross-border payment infrastructure
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <div className="h-3 w-3 bg-green-500 rounded-full animate-pulse">
              </div>

              <span className="text-sm text-gray-600">
                System Online
              </span>
            </div>

          </div>
        </div>
      </header>


      {error && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">

            <p className="text-red-800">
              {error}
            </p>

          </div>
        </div>
      )}


      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        <div className="mb-6">
          <MerchantSelector
            merchants={merchants}
            selectedMerchant={selectedMerchant}
            onMerchantChange={setSelectedMerchant}
          />
        </div>


        {merchantDetails && (
          <>

            <div className="mb-6">
              <Dashboard merchant={merchantDetails} />
            </div>


            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              <div>
                <PayoutForm
                  merchant={merchantDetails}
                  onPayoutCreated={handlePayoutCreated}
                />
              </div>


              <div>
                <LedgerEntries
                  entries={merchantDetails.recent_ledger_entries}
                />
              </div>

            </div>


            <div className="mt-6">
              <PayoutHistory
                key={historyRefreshKey}
                merchantId={selectedMerchant}
              />
            </div>

          </>
        )}

      </main>


      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

          <p className="text-center text-sm text-gray-500">
            Playto Founding Engineer Challenge 2026
          </p>

        </div>
      </footer>

    </div>
  );
}

export default App;