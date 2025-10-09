
`timescale 1 ns / 1 ps
//////////////////////////////////////////////////////////////////////////////////
// Module: rofreqIP_MasterStream
// 
// Purpose: Top-level AXI4-Stream master interface for ring oscillator reliability analysis.
//          Manages a comprehensive measurement system with three ring oscillator types,
//          fixed measurement windows, and synchronized data streaming.
//
// System Overview:
//   - Controls three types of ring oscillators (NOT, NOR, NAND)
//   - Uses fixed measurement window for consistent sampling
//   - Streams 100 consecutive measurements per transaction
//   - Implements full AXI4-Stream protocol handshaking
//
// Parameters:
//   C_M_AXIS_TDATA_WIDTH : Width of AXI Stream data bus (default: 32)
//   C_M_START_COUNT      : Initial delay count before starting transactions (default: 32)
//
// Control Interface:
//   Control Register [31:0]:
//     [0]    - start_run: Start measurement sequence (1 = start)
//     [2:1]  - ro_select: RO type selection
//              00: NOT-based RO
//              01: NOR-based RO
//              10/11: NAND-based RO
//     [31:3] - Reserved for future use
//
//   Runtime Register [31:0]:
//     [31:0] - Measurement configuration (currently fixed to COUNTER_PERIODS)
//
// Operation Sequence:
//   1. Configure RO selection via control register
//   2. Assert start_run bit to begin measurements
//   3. System streams 100 consecutive measurements
//   4. Transaction completes with TLAST assertion
//
// Created: November 2024
// Author : Avishai Kolet
//////////////////////////////////////////////////////////////////////////////////

module rofreqIP_MasterStream #
(
    // AXI Stream interface parameters
    parameter integer C_M_AXIS_TDATA_WIDTH = 32,   // Width of the AXI stream data
    parameter integer C_M_START_COUNT      = 32    // Initial delay count
)
(
    // Ring Oscillator Control Interface
    input  [31:0] controlReg,     // Control register for RO selection and operation
    input  [31:0] runtimeReg,     // Configurable measurement window
    output [2 :0] RO_GPIO_OUT,    // Direct RO outputs for external monitoring

    // AXI Stream Clock and Reset
    input         M_AXIS_ACLK,    // Main clock for AXI interface
    input         M_AXIS_ARESETN, // Active-low reset
    
    // AXI Stream Slave Interface
    input         M_AXIS_TREADY,  // Downstream ready to accept data
    
    // AXI Stream Master Interface
    output        M_AXIS_TVALID,  // Indicates valid data on TDATA
    output [C_M_AXIS_TDATA_WIDTH-1 : 0] M_AXIS_TDATA,   // Frequency measurement data
    output [(C_M_AXIS_TDATA_WIDTH/8)-1 : 0] M_AXIS_TSTRB, // Byte qualifier
    output        M_AXIS_TLAST    // Marks end of measurement sequence

);

//--------------------------------------------------------------------------------
// State Machine Definition
// Controls the measurement and streaming sequence
//--------------------------------------------------------------------------------
    localparam [1:0] IDLE        = 2'b00,  // Waiting for start_run assertion
                     SEND_STREAM  = 2'b01,  // Actively collecting and streaming measurements
                     STREAM_DONE  = 2'b10;  // Completing transaction after all samples sent

    // Configuration Parameters
    localparam NUMBER_OF_OUTPUT_WORDS = 100;  // Fixed number of measurements per transaction

    // State Machine and Control
    (* keep = "true" *) reg [1:0] state;              // Current state of the measurement FSM
    (* keep = "true" *) wire start_run;               // Trigger to start measurement sequence
    (* keep = "true" *) wire [1:0] ro_select;         // Ring oscillator type selection
    
    // Measurement Control and Status
    (* keep = "true" *) reg [31:0] read_pointer;      // Number of samples streamed
    (* keep = "true" *) wire tx_en;                   // Transfer enable for AXI stream
    (* keep = "true" *) reg [C_M_AXIS_TDATA_WIDTH-1 : 0] data_out;  // Register holding current measurement
    
    // Ring Oscillator Interface
    (* keep = "true" *) reg ro_en;                  // Enable signal for ring oscillator
    (* keep = "true" *) wire [C_M_AXIS_TDATA_WIDTH-1 : 0] rofc_out;  // Current RO frequency count
    (* keep = "true" *) wire rofc_valid;              // Indicates valid RO measurement
    
    // Measurement Timing Control
    wire tm_en;                   // Enable signal for measurement window
    wire [31:0] tm_out;          // Current time count



//--------------------------------------------------------------------------------
// Control and Status Signal Assignments
//--------------------------------------------------------------------------------
    // Control Register Decoding
    assign start_run = controlReg[0];     // Measurement sequence trigger
    assign ro_select = controlReg[2:1];   // RO type selection (00:NOT, 01:NOR, 10/11:NAND)

    // AXI4-Stream Interface Signals
    assign M_AXIS_TDATA  = data_out;      // Current measurement value
    assign M_AXIS_TVALID = rofc_valid;    // Data valid when measurement complete
    assign M_AXIS_TSTRB  = {(C_M_AXIS_TDATA_WIDTH/8){1'b1}};  // All bytes valid
    assign M_AXIS_TLAST  = (read_pointer == NUMBER_OF_OUTPUT_WORDS) ? 1'b1 : 1'b0;  // End of sequence marker

//--------------------------------------------------------------------------------
// Measurement Control State Machine
// Manages the complete measurement and streaming sequence
//--------------------------------------------------------------------------------
    always @(posedge M_AXIS_ACLK , negedge M_AXIS_ARESETN) begin
        if(!M_AXIS_ARESETN) begin
            state <= IDLE;                // Reset system to idle
        end
        else begin
            case (state)
                IDLE: begin
                    if(start_run)         // Start new measurement sequence
                        state <= SEND_STREAM;
                end
                
                SEND_STREAM: begin
                    if(read_pointer == NUMBER_OF_OUTPUT_WORDS)  // Check sequence completion
                        state <= STREAM_DONE;
                end
                
                STREAM_DONE: begin
                    state <= IDLE;        // Prepare for next sequence
                end
                
                default: begin
                    state <= IDLE;        // Failsafe recovery
                end
            endcase
        end
    end


//--------------------------------------------------------------------------------
// Measurement Sequence Counter
// Tracks progress through the measurement sequence
//--------------------------------------------------------------------------------
    always @(posedge M_AXIS_ACLK , negedge M_AXIS_ARESETN) begin
        if(!M_AXIS_ARESETN) begin
            read_pointer <= 0;            // Clear counter on reset
        end
        else begin
            if(state == SEND_STREAM) begin
                if(tx_en)                 // Increment on successful transfer
                    read_pointer <= read_pointer + 1;
            end
            else 
                read_pointer <= 0;        // Reset counter in other states
        end
    end
//--------------------------------------------------------------------------------
// AXI Stream Data Output Register
// Manages measurement data output to AXI stream
//--------------------------------------------------------------------------------
    always @(posedge M_AXIS_ACLK , negedge M_AXIS_ARESETN) begin
        if(!M_AXIS_ARESETN) 
            data_out <= 0;               // Clear data on reset
        else begin
            if (state == SEND_STREAM)
                data_out <= rofc_out;    // Output current measurement
            else 
                data_out <= 0;           // Clear data in other states
        end
    end
//--------------------------------------------------------------------------------
// Ring Oscillator Enable Control
// Manages safe activation and deactivation of ring oscillators
//--------------------------------------------------------------------------------
    always @(posedge M_AXIS_ACLK , negedge M_AXIS_ARESETN) begin
        if(!M_AXIS_ARESETN) 
            ro_en <= 0;                  // Ensure safe state on reset
        else begin
            case(state)
                SEND_STREAM:
                    ro_en <= 1;          // Enable selected RO during measurement
                default:
                    ro_en <= 0;          // Disable ROs in all other states
            endcase
        end
    end



//--------------------------------------------------------------------------------
// AXI Stream Transfer Enable Logic
// Controls the timing of data transfers based on handshake signals
//--------------------------------------------------------------------------------
    // always @(posedge M_AXIS_ACLK , negedge M_AXIS_ARESETN) begin
        // if(!M_AXIS_ARESETN) 
            // tx_en <= 0;                  // Clear enable on reset
        // else begin
            // if(M_AXIS_TREADY && rofc_valid)  // Check both downstream ready and data valid
                // tx_en <= 1;              // Enable transfer for one cycle
            // else
                // tx_en <= 0;              // Disable transfer
        // end
    // end

assign tx_en = (M_AXIS_TREADY && rofc_valid) ? 1 : 0 ;
//--------------------------------------------------------------------------------
// Ring Oscillator Frequency Measurement System
// Core measurement subsystem managing all RO variants
//--------------------------------------------------------------------------------
    ro_freq_calc rofc_inst (
        .clk(M_AXIS_ACLK),          // System clock domain
        .nrst(M_AXIS_ARESETN),      // System reset
        .ro_en(ro_en),              // RO activation control
        .ro_select(ro_select),       // RO type selection
        .tx_en(tx_en),         // Data transfer enable
        .rofc_out(rofc_out),        // Frequency measurement output
        .ro_out(RO_GPIO_OUT),       // Direct RO outputs for debug
        .rofc_valid(rofc_valid)     // Measurement valid indicator
    );

    

endmodule
