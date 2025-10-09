`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: tm_counter
// 
// Purpose: Time Measurement Counter
//          Provides a fixed time window for ring oscillator frequency measurements.
//          Counts from 0 to MAX_COUNT, with synchronous restart capability.
//
// Parameters:
//   SIZE       : Counter width (default: 32)
//   MAX_COUNT  : Maximum count value (default: 100)
//
// Inputs:
//   clk        : System clock
//   nrst       : Active-low reset
//   restart    : Synchronous restart signal
//
// Outputs:
//   out        : Current count value
//
// Operation:
//   - Counter increments each clock cycle until MAX_COUNT
//   - Holds at MAX_COUNT until restart
//   - Synchronous restart returns counter to 0
//   - Used for fixed measurement window timing
//
//////////////////////////////////////////////////////////////////////////////////

module tm_counter #( parameter SIZE = 32 , MAX_COUNT = 100 ) (
    // Clock and Control
    input                   clk,      // Clock input (async from RO)
    input                   nrst,     // Active-low reset
    input                   restart,   
    // Counter Outputs
    output reg [SIZE-1:0]   out     // Current count value

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
            if (restart) out <= 0 ;            // Synchronous reset on restart
            else if(out_next < MAX_COUNT + 1 )
                out <= out_next;      // Normal counting operation
        end
    end

endmodule

