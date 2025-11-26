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
// outputs:
//   count        : Current count value
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

	output					ro_stop,
	output					ro_restart

);
    
    // Internal Signals
    wire [SIZE-1:0] count_next;        // Next counter value
    reg [SIZE-1:0]   count;
	reg ro_stop_r;
	reg ro_restart_r;
	wire ro_stop_w;
	wire ro_restart_w;
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
            else if(count_next < MAX_COUNT + 1 )
                count <= count_next;      // Normal counting operation
        end
    end


	always @(*) begin
		if(count == MAX_COUNT)
			ro_stop_r = 1;
		else 
			ro_stop_r = 0;
		
    end
	
	always @(*) begin
		if(count == 0)
			ro_restart_r = 1;
		else
			ro_restart_r = 0;
	end
	
	freq_div #(.DIV_LEN(2)) restart_div (
		.clk(clk),
		.nrst(nrst),
		.in(ro_restart_r),
		.div(ro_restart_w)
	);
	
	freq_div #(.DIV_LEN(2)) stop_div (
		.clk(clk),
		.nrst(nrst),
		.in(ro_stop_r),
		.div(ro_stop_w)
	);
	
	assign ro_stop = ro_stop_w;
	assign ro_restart = ro_restart_w;
	
endmodule

