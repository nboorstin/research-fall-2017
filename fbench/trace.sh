#!/bin/sh
blktrace -d /dev/nvme0n1 -o a.blktrace -w 30
blkparse -i a.blktrace -d a.blkparse -O
btt -i a.blkparse -p a.btt
