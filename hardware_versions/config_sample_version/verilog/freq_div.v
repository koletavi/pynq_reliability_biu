module	freq_div #(parameter DIV_LEN = 2) (
	input clk,
	input nrst,
	input in,
	output div
);
	reg [$clog2(DIV_LEN):0] count;
	reg div_r;
	
	always @ (posedge clk, negedge nrst) begin 
		if(!nrst) begin
			count <= 0;
		end
		else begin
			if(div_r)
				count<=count+1;
			else 
				count <=0;
		end
	end
	
	// counter  	
	always @ (posedge clk, negedge nrst) begin
		if(!nrst) begin
			div_r <=0;
		end
		else begin
			if(in)
				div_r <= 1;
			else if(count == DIV_LEN)
				div_r <= 0;
		end
	end
	
	assign div = div_r;
endmodule