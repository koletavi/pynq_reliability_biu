`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: ring_oscillator_not
// 
// Purpose: NOT Gate-based Ring Oscillator
//          Implements a configurable-length ring oscillator using NOT gates.
//          Part of a multi-RO system for comprehensive reliability analysis
//          using different gate types. Provides baseline oscillation 
//          characteristics for comparison with NOR and NAND variants.
//
// Parameters:
//   RO_LENGTH : Number of inverter stages (default: 21)
//               Must be odd number for proper oscillation
//               Controls base frequency and measurement sensitivity
//
// Inputs:
//   enable   : Active-high enable signal
//              0: Oscillator stopped (output held at 0)
//              1: Oscillator running
//
// Outputs:
//   out      : Oscillator output
//              Base frequency used for reliability measurements
//              Part of three-signal RO output bus [2:0]
//
// Design Notes:
//   - Uses synthesis attributes to prevent optimization
//   - KEEP_HIERARCHY ensures RO structure is preserved
//   - DONT_TOUCH prevents gate merging/removal
//   - Intended for FPGA implementation
//
// Author: Avishai Kolet
// Date  : November 17, 2024
//////////////////////////////////////////////////////////////////////////////////

(* KEEP_HIERARCHY = "yes" *) // Preserve RO structure
module ring_oscillator_not #(parameter RO_LENGTH = 21) (
    input enable,
    output out
    );
   
    (* DONT_TOUCH = "true", KEEP = "true", KEEP_HIERARCHY = "true" *) wire [RO_LENGTH-1:0] nw;


    assign nw[0] = enable ? ~nw[RO_LENGTH-1] : 1'b0;

  generate
    genvar i;
    for (i = 1; i < RO_LENGTH; i = i + 1) begin : ro_luts
      (* DONT_TOUCH = "true", KEEP = "true" *) 
      LUT1 #(
        .INIT(2'b01)         // logical NOT
      ) lut_inst (
        .I0 (nw[i-1]),
        .O  (nw[i])
      );
    end
  endgenerate

  assign out = nw[RO_LENGTH-1];
endmodule
