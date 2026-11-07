module seq_circuit (
    input      CLK,
    input      X,
    input      Y,
    output reg q
);
    wire a, b;
    assign a = X ? (~q) : q;
    assign b = a & (~Y);

    initial q = 1'b0;  // ← only change needed

    always @(posedge CLK) begin
        q <= b;
    end
endmodule