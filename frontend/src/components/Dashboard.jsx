function Dashboard({ merchant }) {
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const balanceCards = [
    {
      title: 'Available Balance',
      amount: merchant.available_balance.rupees,
      subtitle: 'Funds available for withdrawal',
      color: 'green',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
    {
      title: 'Held Balance',
      amount: merchant.held_balance.rupees,
      subtitle: 'Funds held for pending payouts',
      color: 'yellow',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      ),
    },
    {
      title: 'Total Balance',
      amount: merchant.available_balance.rupees + merchant.held_balance.rupees,
      subtitle: 'Total funds in account',
      color: 'blue',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      ),
    },
  ];

  const colorClasses = {
    green: 'bg-green-50 border-green-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    blue: 'bg-blue-50 border-blue-200',
  };

  const iconColorClasses = {
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    blue: 'text-blue-600',
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {balanceCards.map((card, index) => (
        <div
          key={index}
          className={`card border-2 ${colorClasses[card.color]} transition-transform hover:scale-105`}
        >
          <div className="flex items-center justify-between mb-4">
            <div className={iconColorClasses[card.color]}>{card.icon}</div>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${
              card.color === 'green' ? 'bg-green-100 text-green-800' :
              card.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
              'bg-blue-100 text-blue-800'
            }`}>
              {card.title}
            </div>
          </div>
          <div className="mb-2">
            <p className="text-3xl font-bold text-gray-900">
              {formatCurrency(card.amount)}
            </p>
          </div>
          <p className="text-sm text-gray-600">{card.subtitle}</p>
        </div>
      ))}
    </div>
  );
}

export default Dashboard;
