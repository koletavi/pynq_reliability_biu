//////////////////////////////////////////////////////////////////////////////////
// Module: ro_freq_calc
// 
// Purpose: Ring Oscillator Frequency Calculator
//          Manages three different types of ring oscillators (NOT, NOR, NAND),
//          measures their frequencies using a fixed time window approach, and 
//          provides synchronized measurements to the system clock domain.
//
// Parameters:
//   SIZE      : Width of the frequency counter (default: 32)
//
// Inputs:
//   clk       : System clock for synchronous operations
//   nrst      : Active-low reset
//   ro_en     : Ring oscillator enable signal
//   ro_select : Select which RO to measure (00:NOT, 01:NOR, 10/11:NAND)
//
// Outputs:
//   rofc_out  : Synchronized frequency measurement result
//   rofc_valid: Indicates valid measurement data, qualified by sampling complete flag (ssf)
//   ro_out    : Direct ring oscillator outputs [2:0] for debug/monitoring
//
// Operation:
//   1. Measurement is controlled by an internal timer (tm_counter)
//   2. Restart signal triggers new measurement cycle
//   3. Sample Storage Flag (ssf) ensures data validity between measurements
//   4. Fixed measurement window of COUNTER_PERIODS cycles
//   5. Automatic resynchronization of all async domains
//
//////////////////////////////////////////////////////////////////////////////////

module ro_freq_calc #(parameter SIZE = 32)(
    // System Interface
    input                 clk,
    input                 nrst,
    
    // Control Interface
    input                 ro_en,
    input        [1:0]    ro_select,
    input                 tx_en, // data transfer enable signal
    // Measurement Output Interface
    output     [SIZE-1:0] rofc_out,
    output reg               rofc_valid,
    output     [2:0]      ro_out
);

    // Design Parameters
    localparam RO_SIZE = 21;  // Number of stages in each ring oscillator

    localparam COUNTER_PERIODS = 100; // how many periods to count for the RO frequency counter    

    // Ring Oscillator Control
    (* keep = "true" *) wire [2:0] enable;        // Individual enable signals for each RO
    (* keep = "true" *) wire [2:0] ro_wire;       // Direct outputs from ring oscillators
    
    // Asynchronous Counter Outputs (RO clock domain)
    wire [SIZE-1:0] rofc_not_out_async;   // NOT RO frequency count
    wire [SIZE-1:0] rofc_nor_out_async;   // NOR RO frequency count
    wire [SIZE-1:0] rofc_nand_out_async;  // NAND RO frequency count
    
    // Asynchronous valid Signals (RO clock domain)
    wire rofc_not_valid_async;    // NOT counter completion
    wire rofc_nor_valid_async;    // NOR counter completion
    wire rofc_nand_valid_async;   // NAND counter completion
    
    // Synchronized Counter Outputs (System clock domain)
    (* keep = "true" *) wire [SIZE-1:0] rofc_not_out;    // Synchronized NOT count
    (* keep = "true" *) wire [SIZE-1:0] rofc_nor_out;    // Synchronized NOR count
    (* keep = "true" *) wire [SIZE-1:0] rofc_nand_out;   // Synchronized NAND count
    
    // Synchronized valid Signals (System clock domain)
    (* keep = "true" *) wire rofc_not_valid;     // Synchronized NOT valid
    (* keep = "true" *) wire rofc_nor_valid;     // Synchronized NOR valid
    (* keep = "true" *) wire rofc_nand_valid;    // Synchronized NAND valid
    (* keep = "true" *) wire rofc_valid_w;
    (* keep = "true" *) reg rofc_valid_r;


    (* keep = "true" *) reg ssf; // single sample flag
    (* keep = "true" *) reg restart;
    (* keep = "true" *) wire [31:0] tm_src;

    (* keep = "true" *) wire ro_stop;
    (* keep = "true" *) wire ro_restart;

    (* keep = "true" *) reg [31:0] tm_out;    
    (* keep = "true" *) reg [31:0] tm_not;
    (* keep = "true" *) reg [31:0] tm_nor;
    (* keep = "true" *) reg [31:0] tm_nand;
    (* keep = "true" *) reg tm_stop;
    (* keep = "true" *) reg tm_restart;
    (* keep = "true" *) reg ro_stop_not;
    (* keep = "true" *) reg ro_stop_nor;
    (* keep = "true" *) reg ro_stop_nand;
    (* keep = "true" *) reg ro_restart_not;
    (* keep = "true" *) reg ro_restart_nor;
    (* keep = "true" *) reg ro_restart_nand;
    // Ring Oscillator Enable Logic
    // Only one RO is enabled at a time to prevent interference
    // ro_select determines which RO is active when ro_en is high
    assign enable[0] = ro_en & (ro_select == 2'b00);        // NOT RO enable
    assign enable[1] = ro_en & (ro_select == 2'b01);        // NOR RO enable
    assign enable[2] = ro_en & (ro_select == 2'b10 || 
                               ro_select == 2'b11);          // NAND RO enable

    // Restart Control Logic
    // Generates a single-cycle restart pulse when data transfer is enabled
    // Used to initiate a new measurement cycle
    always @(posedge clk or negedge nrst) begin
        if(!nrst) begin
            restart <= 0;  // Clear restart on reset
        end
        else begin
            if (tx_en)  restart <= 1;  // Trigger new measurement
            else        restart <= 0;   // Return to idle
        end
    end

    // Sample Storage Flag (SSF) Logic
    // Controls data validity between measurements:
    // - Sets when timer reaches zero (measurement complete)
    // - Clears when data is transferred (tx_en)
/*
    always @(posedge clk or negedge nrst) begin
        if(!nrst) begin
            ssf <= 0;  // Clear flag on reset
        end
        else begin
	    if (rofc_valid_select) 
	       ssf <= 1;
	    else if (tm_restart)
	       ssf <=0;
        end
    end*/

    //--------------------------------------------------------------------------------
    // Time Measurement Counter
    // Controls the fixed measurement window for RO frequency counting
    // - Counts up to COUNTER_PERIODS
    // - Resets on restart signal
    // - Provides synchronized measurement window across all RO counters
    //--------------------------------------------------------------------------------

    tm_counter #(.SIZE(32), .MAX_COUNT(COUNTER_PERIODS)) tm_counter_inst (
        .clk(clk),          // System clock domain
        .nrst(nrst),        // System reset
        .restart(tx_en),   // Start new measurement cycle
		.ro_stop(ro_stop),
		.ro_restart(ro_restart)
        //.out(tm_src)        // Current count value
    );

    //--------------------------------------------------------------------------------
    // Clock Domain Crossing Synchronizers + Synchronizing delay
    // Safe transfer of counter values from system clock domain to RO clock domains 
    // Uses multi-stage synchronization to prevent metastability
    //--------------------------------------------------------------------------------

    reg [1:0] c2r_sync_not;
    reg [1:0] c2r_sync_nor;
    reg [1:0] c2r_sync_nand;
    reg [1:0] sync_delay;
    
    // synchronizing clock delay due to synchronizers
    always @ (posedge clk, negedge  nrst) begin
        if( !nrst ) begin
            sync_delay <= 0 ; 
            tm_stop <= 0 ;
			tm_restart <= 0;
        end
        else begin
            sync_delay <= {ro_restart,ro_stop};
            tm_stop <= sync_delay[0];
			tm_restart <= sync_delay[1];
        end
    end
    
    //synchronizer from clock domain to ring oscillator not
    always @ (posedge ro_wire[0], negedge  nrst) begin
        if( !nrst ) begin
            c2r_sync_not <= 0 ; 
            ro_stop_not <= 0 ;
			ro_restart_not <= 0 ;
        end
        else begin
            c2r_sync_not[0] <= ro_stop;
            c2r_sync_not[1] <= ro_restart;
            ro_stop_not <= c2r_sync_not[0];
			ro_restart_not <= c2r_sync_not[1];
        end
    end
    
    //synchronizer from clock domain to ring oscillator nor
    always @ (posedge ro_wire[1], negedge  nrst) begin
        if( !nrst ) begin
            c2r_sync_nor <= 0 ; 
            ro_stop_nor <= 0 ;
			ro_restart_nor <= 0 ;
        end
        else begin
            c2r_sync_nor[0] <= ro_stop;
            c2r_sync_nor[1] <= ro_restart;
            ro_stop_nor <= c2r_sync_nor[0];
			ro_restart_nor <= c2r_sync_nor[1];
        end
    end
    
    //synchronizer from clock domain to ring oscillator nand
    always @ (posedge ro_wire[2], negedge  nrst) begin
        if( !nrst ) begin
            c2r_sync_nand <= 0 ; 
            ro_stop_nand <= 0 ;
			ro_restart_nand <= 0 ;
        end
        else begin
            c2r_sync_nand[0] <= ro_stop;
            c2r_sync_nand[1] <= ro_restart;
            ro_stop_nand <= c2r_sync_nand[0];
			ro_restart_nand <= c2r_sync_nand[1];
        end
    end

    //--------------------------------------------------------------------------------
    // Ring Oscillator Instantiations
    // Each RO is constructed with different logic gates to observe variations
    // in oscillation frequency due to different gate characteristics
    //--------------------------------------------------------------------------------

    // NOT-based Ring Oscillator
    // Uses inverters for potentially fastest oscillation
    ring_oscillator_not #(.RO_LENGTH(RO_SIZE)) RO_not_inst (
        .enable(enable[0]),    // Controlled by ro_select == 2'b00
        .out(ro_wire[0])      // Direct oscillator output
    );

    // NOR-based Ring Oscillator
    // Uses NOR gates for different delay characteristics
    ring_oscillator_nor #(.RO_LENGTH(RO_SIZE)) RO_nor_inst (
        .enable(enable[1]),    // Controlled by ro_select == 2'b01
        .out(ro_wire[1])      // Direct oscillator output
    );

    // NAND-based Ring Oscillator
    // Uses NAND gates for yet another delay characteristic
    ring_oscillator_nand #(.RO_LENGTH(RO_SIZE)) RO_nand_inst (
        .enable(enable[2]),    // Controlled by ro_select == 2'b10/11
        .out(ro_wire[2])      // Direct oscillator output
    );

    //--------------------------------------------------------------------------------
    // Frequency Counter Instantiations
    // Each counter measures its respective RO's frequency during the
    // measurement window defined by tm_en
    //--------------------------------------------------------------------------------

    // NOT RO Frequency Counter
    ro_counter #(.SIZE(SIZE)) ro_not_counter (
        .clk(ro_wire[0]),              // Counts RO oscillations
        .nrst(nrst),                // System reset
        .tm_stop(ro_stop_not),
		.tm_restart(ro_restart_not),   
        .out(rofc_not_out_async),      // Asynchronous count value
        .valid(rofc_not_valid_async)   // Measurement complete flag
    );

    // NOR RO Frequency Counter
    ro_counter #(.SIZE(SIZE)) ro_nor_counter (
        .clk(ro_wire[1]),              // Counts RO oscillations
        .nrst(nrst),                // System reset
        .tm_stop(ro_stop_nor),
		.tm_restart(ro_restart_nor),   
        .out(rofc_nor_out_async),      // Asynchronous count value
        .valid(rofc_nor_valid_async)   // Measurement complete flag
    );

    // NAND RO Frequency Counter
    ro_counter #(.SIZE(SIZE)) ro_nand_counter (
        .clk(ro_wire[2]),              // Counts RO oscillations
        .nrst(nrst),                // System reset
        .tm_stop(ro_stop_nand),
		.tm_restart(ro_restart_nand),   
        .out(rofc_nand_out_async),     // Asynchronous count value
        .valid(rofc_nand_valid_async)  // Measurement complete flag
    );

    //--------------------------------------------------------------------------------
    // Clock Domain Crossing Synchronizers
    // Safe transfer of counter values from RO clock domains to system clock domain
    // Uses multi-stage synchronization to prevent metastability
    //--------------------------------------------------------------------------------

    // NOT RO Synchronizer
    synchronizer not_sync_inst (
        .clk(clk),                     // System clock
        .nrst(nrst),                   // System reset
        .async_in(rofc_not_out_async), // Async counter value
        .valid_in(rofc_not_valid_async), // Async valid signal
        .sync_out(rofc_not_out),       // Synchronized counter value
        .valid_out(rofc_not_valid)     // Synchronized valid signal
    );

    // NOR RO Synchronizer
    synchronizer nor_sync_inst (
        .clk(clk),                     // System clock
        .nrst(nrst),                   // System reset
        .async_in(rofc_nor_out_async), // Async counter value
        .valid_in(rofc_nor_valid_async), // Async valid signal
        .sync_out(rofc_nor_out),       // Synchronized counter value
        .valid_out(rofc_nor_valid)     // Synchronized valid signal
    );

    // NAND RO Synchronizer
    synchronizer nand_sync_inst (
        .clk(clk),                     // System clock
        .nrst(nrst),                   // System reset
        .async_in(rofc_nand_out_async), // Async counter value
        .valid_in(rofc_nand_valid_async), // Async valid signal
        .sync_out(rofc_nand_out),      // Synchronized counter value
        .valid_out(rofc_nand_valid)    // Synchronized valid signal
    );

    //--------------------------------------------------------------------------------
    // Output Multiplexer and Validation Logic
    // Manages the selection and validation of RO measurements
    //--------------------------------------------------------------------------------

    // valid Signal Selection and Qualification
    // - Selects appropriate valid signal based on RO type
    // - Qualifies with Sample Storage Flag (ssf) for synchronized output
    assign rofc_valid_w = (ro_select == 2'b00) ? rofc_not_valid :  // NOT RO
                       (ro_select == 2'b01) ? rofc_nor_valid :          // NOR RO
                       (ro_select == 2'b10 || ro_select == 2'b11) ?     // NAND RO
                       rofc_nand_valid : 0;                             // Default


    always @ (posedge clk, negedge nrst) begin
        if(!nrst) begin
            rofc_valid_r <= 0;
        end
        else begin
                rofc_valid_r <= rofc_valid_w;
        end
    end


    // Final Valid Signal
    // Combines RO-specific valid signal with sample storage flag
    // Ensures data is only valid when measurement is complete and stored
   always @ (posedge clk, negedge nrst) begin
        if(!nrst) begin
            rofc_valid <= 0;
        end
        else begin
            if(rofc_valid_w && !rofc_valid_r)
                rofc_valid <= 1 ;
            else
            if(tx_en)
                rofc_valid <= 0 ;
        end
    end
    // Measurement Output Selection
    // Routes the selected RO's frequency measurement to output
    // Output is qualified by rofc_valid signal
    assign rofc_out = (ro_select == 2'b00) ? rofc_not_out :            // NOT RO
                     (ro_select == 2'b01) ? rofc_nor_out :             // NOR RO
                     (ro_select == 2'b10 || ro_select == 2'b11) ?      // NAND RO
                     rofc_nand_out : 0;                                // Default

    // Direct RO Output Assignment
    // Provides direct access to RO outputs for debugging/monitoring
    assign ro_out = ro_wire;

endmodule

