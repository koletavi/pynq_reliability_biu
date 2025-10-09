`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: ro_counter
// 
// Purpose: Ring Oscillator Event Counter
//          Counts oscillation events from a ring oscillator within a fixed
//          time window defined by tm_count. Provides count value and valid
//          signal when measurement window completes.
//
// Parameters:
//   MAX_COUNT : Maximum count value (default: 100)
//   SIZE      : Counter width, automatically sized based on MAX_COUNT
//
// Inputs:
//   clk       : Clock input from ring oscillator (asynchronous domain)
//   nrst      : Active-low reset
//   tm_count  : Time measurement counter value from system domain
//
// Outputs:
//   out       : Current count value [SIZE-1:0]
//   valid     : Indicates measurement completion
//
// Operation:
//   - Counts RO events while tm_count < MAX_COUNT
//   - Holds count and asserts valid when tm_count reaches MAX_COUNT
//   - Resets count when tm_count returns to 0
//   - Operates in RO clock domain, needs synchronization for system domain
//
//////////////////////////////////////////////////////////////////////////////////

module ro_counter #(parameter MAX_COUNT = 100 , SIZE = $clog2(MAX_COUNT) ) (
    // Clock and Control
    input                   clk,      // Clock input (async from RO)
    input                   nrst,     // Active-low reset
    input  [SIZE-1:0]       tm_count, // time counter value
    
    // Counter Outputs
    output reg [SIZE-1:0]   out,      // Current count value
    output reg              valid     // Measurement complete flag
);
    
    // Internal Signals
    wire [SIZE-1:0] out_next;        // Next counter value
    
//--------------------------------------------------------------------------------
    // Counter Logic
    // Implements basic counting functionality with synchronous control
    //--------------------------------------------------------------------------------
    
    // Next State Logic
    assign out_next = out + 1;       // Simple increment
    
    // Counter Value Sequential Logic
    // Controls the counting sequence and reset behavior
    always @(posedge clk, negedge nrst) begin
        if(!nrst) begin
            out <= 0;                 // Asynchronous reset
        end
        else begin
            if(tm_count == 0) out <= 0 ;            // Synchronous reset on restart
            else if(tm_count < MAX_COUNT)
                out <= out_next;      // Normal counting operation
            else 
                out <= out;           // hold the count when tm_count reached MAX_COUNT
        end
    end
    
    

    // Valid Signal Sequential Logic
    // Indicates when measurement is complete and data is valid
    always @(posedge clk, negedge nrst) begin
        if(!nrst) begin
            valid <= 0;              // Clear valid on reset
        end
        else begin
            if ( tm_count == MAX_COUNT )
                valid <= 1;          // Set valid when measurement window ends
            else 
                valid <= 0;          // Clear valid otherwise
        end
    end

endmodule

