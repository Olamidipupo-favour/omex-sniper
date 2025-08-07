// Test frontend position handling
console.log('🧪 Testing frontend position handling...');

// Clear any existing positions first
if (window.app) {
    window.app.positions = [];
    console.log('🧹 Cleared existing positions');
}

// Simulate a position update event
const testPositionData = {
    action: 'buy',
    mint: 'Gwc5W5mivb9MVaBkFwUjaW5R3UL9CZChnFC54GfYpump',
    token_symbol: 'Dunny',
    token_name: 'Dunny Token',
    sol_amount: 0.000001,
    token_amount: 29.559227,
    entry_price: 0.000000033830
};

console.log('📊 Test position data:', testPositionData);

// Call the position update handler
if (window.app && window.app.handlePositionUpdate) {
    console.log('✅ Calling handlePositionUpdate...');
    window.app.handlePositionUpdate(testPositionData);
    
    // Check if position was added
    setTimeout(() => {
        console.log('📊 Current positions array:', window.app.positions);
        console.log('📊 Positions count:', window.app.positions.length);
        
        // Check if the position table was updated
        const tbody = document.querySelector('#positions-table tbody');
        if (tbody) {
            console.log('📋 Table body content length:', tbody.innerHTML.length);
            console.log('📋 Table body content:', tbody.innerHTML);
        } else {
            console.error('❌ Could not find positions table body');
        }
        
        // Check header stats
        const activePositionsElement = document.getElementById('activePositions');
        if (activePositionsElement) {
            console.log('📊 Active positions in header:', activePositionsElement.textContent);
        }
        
        console.log('✅ Test completed!');
    }, 1000);
} else {
    console.error('❌ App not found or handlePositionUpdate not available');
} 