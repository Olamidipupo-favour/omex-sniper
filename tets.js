const findHolders = async () => {
     // Pagination logic
     let page = 1;
        // allOwners will store all the addresses that hold the token
     let allOwners = new Set();
   
     while (true) {
       const response = await fetch(url, {
         method: "POST",
         headers: {
           "Content-Type": "application/json",
         },
         body: JSON.stringify({
           jsonrpc: "2.0",
           method: "getTokenAccounts",
           id: "helius-test",
           params: {
             page: page,
             limit: 1000,
             displayOptions: {},
                       //mint address for the token we are interested in
             mint: "CKfatsPMUf8SkiURsDXs7eK6GWb4Jsd6UDbs7twMCWxo",
           },
         }),
       });
   
           // Check if any error in the response
         if (!response.ok) {
           console.log(
             `Error: ${response.status}, ${response.statusText}`
           );
           break;
         }
   
       const data = await response.json();
     	// Pagination logic. 
       if (!data.result || data.result.token_accounts.length === 0) {
         console.log(`No more results. Total pages: ${page - 1}`);
         break;
       }
       console.log(`Processing results from page ${page}`);
            // Adding unique owners to a list of token owners. 
       data.result.token_accounts.forEach((account) =>
         allOwners.add(account.owner)
       );
       page++;
     }
   
     fs.writeFileSync(
       "output.json",
       JSON.stringify(Array.from(allOwners), null, 2)
     );
   };

   findHolders();