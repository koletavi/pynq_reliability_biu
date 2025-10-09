`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: ring_oscillator_nor
// 
// Purpose: NOR Gate-based Ring Oscillator
//          Implements a configurable-length ring oscillator using NOR gates
//          with tied inputs. Part of a three-RO system providing different
//          delay characteristics for comprehensive reliability analysis.
//
// Parameters:
//   RO_LENGTH : Number of NOR gate stages (default: 21)
//               Must be odd number for proper oscillation
//               Matched with NOT and NAND RO lengths for comparison
//
// Inputs:
//   enable   : Active-high enable signal
//              0: Oscillator stopped (output held at 0)
//              1: Oscillator running
//
// Outputs:
//   out      : Oscillator output
//              Second signal in three-signal RO output bus [2:0]
//              Selected when ro_select = 2'b01
//
// Design Notes:
//   - Uses synthesis attributes to prevent optimization
//   - KEEP_HIERARCHY ensures RO structure is preserved
//   - DONT_TOUCH prevents gate merging/removal
//   - NOR gates with tied inputs provide different delay than simple inverters
//
// Author: Avishai Kolet
// Date  : November 17, 2024
//////////////////////////////////////////////////////////////////////////////////

(* KEEP_HIERARCHY = "yes" *) // Preserve RO structure
module ring_oscillator_nor #(parameter RO_LENGTH = 21) (
    input enable,
    output out
    );
    
     (* KEEP *) wire [RO_LENGTH:0] nw ;
    genvar i ;
    
    generate 
        for ( i=0 ; i <RO_LENGTH ; i=i+1) begin
           (* DONT_TOUCH *) nor(nw[i+1],nw[i],nw[i]);
        end
    endgenerate 
    
    assign nw[0] = enable ? nw[RO_LENGTH] : 0 ;
    assign out = nw[RO_LENGTH] ; 
endmodule
