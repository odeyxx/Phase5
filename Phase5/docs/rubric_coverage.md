# Phase 5 Rubric Coverage

## Core correctness

- File transfer over UDP using TCP-like segments
- SYN / SYN-ACK / ACK setup
- FIN / ACK teardown
- Segment fields: seq, ack, checksum, flags, rwnd, payload
- Cumulative ACKs
- Retransmission logic
- In-order receiver reassembly

## Flow control

- Receiver advertises rwnd
- Sender obeys rwnd
- Sender uses min(cwnd, rwnd)

## Congestion control

- Slow start
- Congestion avoidance
- Triple duplicate ACK detection
- Fast retransmit
- Fast recovery
- Timeout response with cwnd reduction and ssthresh update

## Demo options

- Option 1: normal transfer
- Option 2: flow-control-limited transfer
- Option 3: visible slow start
- Option 4: triple duplicate ACK / fast recovery
- Option 5: timeout recovery

## Plots

- Chart 1: completion time vs packet loss rate
- Chart 2: cwnd vs transmission round
- Chart 3: Phase 1 to Phase 5 comparison
