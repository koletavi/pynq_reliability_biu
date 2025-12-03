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
    output reg [SIZE-1:0] rofc_out,
    output reg            valid,
    output     [2:0]      ro_out
);

    // Design Parameters
    localparam RO_SIZE_1 = 11;  // Number of stages in each ring oscillator
    localparam RO_SIZE_2 = 21; // currently only using 21-stage RO
    localparam RO_SIZE_3 = 51; // Number of stages in each ring oscillator

    localparam COUNTER_PERIODS = 100; // how many periods to count for the RO frequency counter

    // Ring Oscillator Control
    (* keep = "true" *) reg [2:0] enable;        // Individual enable signals for each RO
    (* keep = "true" *) wire [2:0] ro_wire;       // Direct outputs from ring oscillators
    
    
    // Synchronized Counter Outputs (System clock domain)
    (* keep = "true" *) wire [SIZE-1:0] rofc_out_b [2:0];    // Synchronized NOT count
    
    // Synchronized valid Signals (System clock domain)
    (* keep = "true" *) wire [2:0] rofc_valid_b;     // Synchronized NOT valid
    (* keep = "true" *) wire rofc_valid_w;
    (* keep = "true" *) reg rofc_valid_r;
    (* keep = "true" *) reg rofc_valid;

    (* keep = "true" *) wire tm100; // reached 100 counts signal from tm_counter
    (* keep = "true" *) reg restart; // restart signal for ro_counter and tm_counter

    (* keep = "true" *) wire [SIZE-1:0] rofc_out_w; 
    (* keep = "true" *) reg stop;


    (* keep = "true" *) reg [1:0] state;
    (* keep = "true" *) reg [1:0] next_state;


    //--------------------------------------------------------------------------------

    // Control Logic

    //--------------------------------------------------------------------------------

    always@(*) begin
        case(state)
            // RESTART STATE
            2'b00: begin
                next_state = 2'b01;
            end
            // CALC STATE
            2'b01: begin
                if (tm100)
                    next_state = 2'b10;
                else
                    next_state = 2'b01;
            end
            // STOP STATE
            2'b10: begin
                if (rofc_valid)
                    next_state = 2'b11;
                else
                    next_state = 2'b10;
            end
            // READ STATE
            2'b11: begin
                if (tx_en)
                    next_state = 2'b00;
                else
                    next_state = 2'b11;
            end
            default: begin 
                next_state = 2'b00;
            end
        endcase
    end

    always @ (posedge clk, negedge  nrst) begin
        if( !nrst ) begin
            restart <= 0 ;
            stop <= 0 ;
            valid <= 0 ;
        end
        else begin
            case(state)
                // RESTART STATE
                2'b00: begin
                    restart <= 1 ;
                    stop <= 0 ;
                    valid <= 0 ;
                end
                // CALC STATE
                2'b01: begin
                    restart <= 0 ;
                    stop <= 0 ;
                    valid <= 0 ;
                end
                // STOP STATE
                2'b10: begin
                    restart <= 0 ;
                    stop <= 1 ;
                    valid <= 0 ;
                end
                // READ STATE
                2'b11: begin
                    restart <= 0 ;
                    stop <= 1 ;
                    valid <= 1 ;
                end
                default: begin 
                    restart <= 0 ;
                    stop <= 0 ;
                    valid <= 0 ;
                end
            endcase
        end
    end

    always @ (posedge clk, negedge  nrst) begin
        if( !nrst ) begin
            state <= 2'b00 ;
        end
        else begin
            state <= next_state ;
        end
    end

    //--------------------------------------------------------------------------------

    // Ring Oscillator Enable Logic
    always @ (posedge clk, negedge  nrst) begin
        if( !nrst ) begin
            enable <= {3{1'b0}} ;
        end
        else begin
            if (ro_en) begin
                enable <= {3{1'b1}} ;
            end
        end
    end

    //--------------------------------------------------------------------------------
    // Time Measurement Counter
    // Controls the fixed measurement window for RO frequency counting
    // - Counts up to COUNTER_PERIODS
    // - Resets on restart signal
    // - Provides synchronized measurement window across all RO counters
    //--------------------------------------------------------------------------------

    tm_counter #(.SIZE(SIZE), .MAX_COUNT(COUNTER_PERIODS)) tm_counter_inst (
        .clk(clk),          // System clock domain
        .nrst(nrst),        // System reset
        .restart(restart),   // Start new measurement cycle
		.tm100(tm100)
    );


    rof_test_module #(.DIV_LEN(1), .SIZE(SIZE), .RO_LENGTH(RO_SIZE_1)) rof_11step_inst (
        .clk(clk),
        .nrst(nrst),
        .enable(enable[0]),
        .stop(stop),
        .restart(restart),
        .rofc_out(rofc_out_b[0]),
        .rofc_valid(rofc_valid_b[0]),
        .ro_clk(ro_wire[0])
    );

    rof_test_module #(.DIV_LEN(2), .SIZE(SIZE), .RO_LENGTH(RO_SIZE_2)) rof_21step_inst (
        .clk(clk),
        .nrst(nrst),
        .enable(enable[1]),
        .stop(stop),
        .restart(restart),
        .rofc_out(rofc_out_b[1]),
        .rofc_valid(rofc_valid_b[1]),
        .ro_clk(ro_wire[1])
    );  

    rof_test_module #(.DIV_LEN(4), .SIZE(SIZE), .RO_LENGTH(RO_SIZE_3)) rof_51step_inst (
        .clk(clk),
        .nrst(nrst),
        .enable(enable[2]),
        .stop(stop),
        .restart(restart),
        .rofc_out(rofc_out_b[2]),
        .rofc_valid(rofc_valid_b[2]),
        .ro_clk(ro_wire[2])
    );  

    //--------------------------------------------------------------------------------
    // Output Multiplexer and Validation Logic
    // Manages the selection and validation of RO measurements
    //--------------------------------------------------------------------------------

    // valid Signal Selection and Qualification
    // - Selects appropriate valid signal based on RO type
    // - Qualifies with Sample Storage Flag (ssf) for synchronized output
    assign rofc_valid_w = (ro_select == 2'b00) ? rofc_valid_b[0] :  // NOT RO
                       (ro_select == 2'b01) ? rofc_valid_b[1] :          // NOR RO
                       (ro_select == 2'b10 || ro_select == 2'b11) ?     // NAND RO
                       rofc_valid_b[2] : 0;                             // Default


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
                rofc_valid <= 0 ;
        end
    end

    // Measurement Output Selection
    // Routes the selected RO's frequency measurement to output
    // Output is qualified by rofc_valid signal
    assign rofc_out_w = (ro_select == 2'b00) ? rofc_out_b[0] :            // 11 RO
                     (ro_select == 2'b01) ? rofc_out_b[1] :             // 21 RO
                     (ro_select == 2'b10 || ro_select == 2'b11) ?      // 51 RO
                     rofc_out_b[2] : 0;                               

    always @ (posedge clk, negedge nrst) begin
        if(!nrst) begin
            rofc_out <= 0;
        end
        else begin
            if(rofc_valid)
                rofc_out <= rofc_out_w ;
        end
    end

    // Direct RO Output Assignment
    // Provides direct access to RO outputs for debugging/monitoring
    assign ro_out = ro_wire;

endmodule