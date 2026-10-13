`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module: ring_oscillator_nand
// 
// Purpose: NAND Gate-based Ring Oscillator
//          Implements a configurable-length ring oscillator using NAND gates
//          with tied inputs. Completes the three-RO system by providing a
//          third unique delay characteristic for reliability analysis.
//
// Parameters:
//   RO_LENGTH : Number of NAND gate stages (default: 21)
//               Must be odd number for proper oscillation
//               Matched length with NOT and NOR variants
//
// Inputs:
//   enable   : Active-high enable signal
//              0: Oscillator stopped (output held at 0)
//              1: Oscillator running (selected by ro_select = 2'b10/11)
//
// Outputs:
//   out      : Oscillator output
//              Third signal in three-signal RO output bus [2:0]
//              Used for comprehensive gate delay analysis
//
// Design Notes:
//   - Uses synthesis attributes to prevent optimization
//   - KEEP_HIERARCHY ensures RO structure is preserved
//   - DONT_TOUCH prevents gate merging/removal
//   - NAND gates with tied inputs provide third delay characteristic
//   - Used with NOT and NOR ROs for comprehensive analysis
//
// Author: Avishai Kolet
// Date  : November 17, 2024
//////////////////////////////////////////////////////////////////////////////////

(* KEEP_HIERARCHY = "yes" *) // Preserve RO structure
module ring_oscillator_nand #(parameter RO_LENGTH = 21) (
    input enable,
    output out
    );
    
     (* KEEP *) wire [RO_LENGTH:0] nw ;
    genvar i ;
    
    generate 
        for ( i=0 ; i <RO_LENGTH ; i=i+1) begin
           (* DONT_TOUCH *) nand(nw[i+1],nw[i],nw[i]);
        end
    endgenerate 
    
    assign nw[0] = enable ? nw[RO_LENGTH] : 0 ;
    assign out = nw[RO_LENGTH] ; 
endmodule
