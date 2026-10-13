`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: tm_counter
// 
// Purpose: Time Measurement Counter
//          Provides a fixed time window for ring oscillator frequency measurements.
//          Counts from 0 to runtime, with synchronous restart capability.
//
// Parameters:
//   SIZE       : Counter width (default: 32)
//
// Inputs:
//   clk        : System clock
//   nrst       : Active-low reset
//   restart    : Synchronous restart signal
//   runtime    : max time the counter reaches bedroe reading RO frequency value
//
// outputs:
//   count        : Current count value
//
// Operation:
//   - Counter increments each clock cycle until runtime
//   - Holds at runtime until restart
//   - Synchronous restart returns counter to 0
//   - Used for fixed measurement window timing
//
//////////////////////////////////////////////////////////////////////////////////

module tm_counter #( parameter SIZE = 32 ) (
    // Clock and Control
    input                   clk,      // Clock input (async from RO)
    input                   nrst,     // Active-low reset
    input [SIZE-1:0]        runtime,
    input                   restart,   

	output					tm100

);
    
    // Internal Signals
    wire [SIZE-1:0] count_next;        // Next counter value
    reg [SIZE-1:0]   count;
    wire ro_stop_w;
	reg ro_stop_r;
    reg ro_stop;
	
//--------------------------------------------------------------------------------
    // Counter Logic
    // Implements basic counting functionality with synchronous control
    //--------------------------------------------------------------------------------
    
    // Next State Logic
    assign count_next = count + 1;       // Simple increment
    
    // Counter Value Sequential Logic
    // Controls the counting sequence and reset behavior
    always @(posedge clk, negedge nrst) begin
        if(!nrst) begin
            count <= 0;                 // Asynchronous reset
        end
        else begin
            if (restart) count <= 0 ;            // Synchronous reset on restart
            else if(count_next < runtime + 1 )
                count <= count_next;      // Normal counting operation
        end
    end

    assign ro_stop_w = (count == runtime) ? 1'b1 : 1'b0;

	always @(posedge clk, negedge nrst) begin
        if(!nrst) begin
            ro_stop_r <= 1'b0;                 // Asynchronous reset
        end
        else begin
            ro_stop_r <= ro_stop_w;
        end
		
    end
	
    always @(posedge clk, negedge nrst) begin
        if(!nrst) begin
            ro_stop <= 1'b0;                 // Asynchronous reset
        end
        else begin
            if (ro_stop_w && !ro_stop_r)
                ro_stop <= 1'b1;
            else
                ro_stop <= 1'b0;
        end
        
    end
	
	assign tm100 = ro_stop;
	
endmodule

