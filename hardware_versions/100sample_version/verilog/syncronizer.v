//////////////////////////////////////////////////////////////////////////////////
// Module: synchronizer
// 
// Purpose: Multi-bit Clock Domain Crossing (CDC) Synchronizer
//          Safely transfers RO counter values and valid signals from the
//          ring oscillator clock domain to the system clock domain using
//          a two-stage synchronization scheme.
//
// Parameters:
//   SIZE     : Width of the data bus to synchronize (default: 32)
//              Must match the width of the RO counter output
//
// Inputs:
//   clk      : System clock (destination domain)
//   nrst     : Active-low reset
//   async_in : RO counter value from RO domain [SIZE-1:0]
//   valid_in : Measurement complete flag from RO domain
//
// Outputs:
//   sync_out : Synchronized counter value in system domain [SIZE-1:0]
//   valid_out: Synchronized valid signal in system domain
//
// Operation:
//   - Uses two-stage synchronization for metastability mitigation
//   - Synchronizes both counter value and valid signal
//   - Assumes input remains stable during synchronization window
//   - All registers reset to 0 on active-low reset
//   - Adds 2 clock cycle latency to signal path
//
// Design Notes:
//   - Uses two-stage synchronization for metastability mitigation
//   - Assumes input stable during synchronization
//   - Both data and control signals are synchronized
//   - Add more stages if needed for higher MTBF
//   - Critical for reliable clock domain crossing
//
//////////////////////////////////////////////////////////////////////////////////

module syncronizer #(parameter SIZE = 32)(
    // Clock and Reset
    input                 clk,       // Destination clock
    input                 nrst,      // Active-low reset
    
    // Source Domain Interface
    input      [SIZE-1:0] async_in,  // Async data input
    input                 valid_in,   // Async valid signal
    
    // Destination Domain Interface
    output     [SIZE-1:0] sync_out,  // Synchronized data
    output                valid_out   // Synchronized valid
);

    // Synchronization Registers
    // Two-stage synchronization chain for both data and control
    reg [SIZE-1:0] sync_intermediate [1:0];  // Data synchronization stages
    reg            valid_intermediate [1:0];  // valid signal synchronization stages

    assign sync_out = sync_intermediate[1];
    assign valid_out = valid_intermediate[1];

    //--------------------------------------------------------------------------------
    // Two-Stage Synchronization Process
    // Implements double flip-flop synchronization for both data and valid signal
    // to prevent metastability in the destination clock domain
    //--------------------------------------------------------------------------------
    always @(posedge clk, negedge nrst) begin
        if(!nrst) begin
            // Reset all synchronization registers
            sync_intermediate[0]  <= 0;   // First stage data
            sync_intermediate[1]  <= 0;   // Second stage data
            valid_intermediate[0] <= 0;   // First stage valid
            valid_intermediate[1] <= 0;   // Second stage valid
        end
        else begin
            // Data Synchronization Path
            sync_intermediate[0]  <= async_in;           // Sample async input
            sync_intermediate[1]  <= sync_intermediate[0]; // First -> second stage
         
            // valid Signal Synchronization Path
            valid_intermediate[0] <= valid_in;           // Sample async valid
            valid_intermediate[1] <= valid_intermediate[0]; // First -> second stage
        end
    end

    //--------------------------------------------------------------------------------
    // Implementation Notes:
    // 1. Data must be stable in source domain during synchronization window
    // 2. Synchronization adds 2-3 clock cycle latency
    // 3. No data coherency check implemented - assumes slow-changing data
    // 4. valid signal synchronization handles control flow
    // 5. Additional synchronization stages can be added if needed
    //--------------------------------------------------------------------------------

endmodule