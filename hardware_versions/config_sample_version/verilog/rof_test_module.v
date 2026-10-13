module rof_test_module #( parameter 
    DIV_LEN = 2, 
    RO_LENGTH = 21, 
    SIZE = 32
) (
    input clk,
    input nrst,
    input enable,
    input stop,
    input restart,
    output [SIZE-1:0] rofc_out,
    output  rofc_valid,
    output ro_clk
);

    wire stop_wide;
    wire restart_wide;

    reg [1:0] c2r_sync;
    reg ro_stop;
    reg ro_restart;

    (* DONT_TOUCH = "true", KEEP = "true", MARK_DEBUG = "true" *) wire ro_clk_w;
    wire [SIZE-1:0] rofc_out_async;
    wire rofc_valid_async;
    

    // Instantiate frequency dividers for stop and restart signals
    freq_div #(.DIV_LEN(DIV_LEN)) stop_div (
		.clk(clk),
		.nrst(nrst),
		.in(stop),
		.div(stop_wide)
	);

    freq_div #(.DIV_LEN(DIV_LEN)) restart_div (
		.clk(clk),
		.nrst(nrst),
		.in(restart),
		.div(restart_wide)
	);


    //synchronizer from clock domain to ring oscillator not
    always @ (posedge ro_clk, negedge  nrst) begin
        if( !nrst ) begin
            c2r_sync <= 0 ; 
            ro_stop <= 0 ;
			ro_restart <= 0 ;
        end
        else begin
            c2r_sync[0] <= stop_wide;
            c2r_sync[1] <= restart_wide;
            ro_stop <= c2r_sync[0];
			ro_restart <= c2r_sync[1];
        end
    end

    
    // NOT-based Ring Oscillator
    // Uses inverters for potentially fastest oscillation
    ring_oscillator_not #(.RO_LENGTH(RO_LENGTH)) RO_not_inst (
        .enable(enable),    // Controlled by ro_select == 2'b00
        .out(ro_clk_w)      // Direct oscillator output
    );

    // RO Frequency Counter
    ro_counter #(.SIZE(SIZE)) ro_not_counter (
        .clk(ro_clk_w),              // Counts RO oscillations
        .nrst(nrst),                // System reset
        .stop(ro_stop),
		.restart(ro_restart),   
        .out(rofc_out_async),      // Asynchronous count value
        .valid(rofc_valid_async)   // Measurement complete flag
    );

    // RO Synchronizer
    synchronizer sync_inst (
        .clk(clk),                     // System clock
        .nrst(nrst),                   // System reset
        .async_in(rofc_out_async), // Async counter value
        .valid_in(rofc_valid_async), // Async valid signal
        .sync_out(rofc_out),       // Synchronized counter value
        .valid_out(rofc_valid)     // Synchronized valid signal
    );

    assign ro_clk = ro_clk_w;

endmodule