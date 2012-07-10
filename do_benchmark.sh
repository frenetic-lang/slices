echo "waxman multicast"
for i in {1..10}; do ./benchmark.py --vtime --waxman --multicast; done
echo "waxman shortest"
for i in {1..10}; do ./benchmark.py --vtime --waxman --shortest; done
echo "smallworld multicast"
for i in {1..10}; do ./benchmark.py --vtime --smallworld --multicast; done
echo "smallworld shortest"
for i in {1..10}; do ./benchmark.py --vtime --smallworld --shortest; done
echo "fattree multicast"
for i in {1..10}; do ./benchmark.py --vtime --fattree --multicast; done
echo "fattree shortest"
for i in {1..10}; do ./benchmark.py --vtime --fattree --shortest; done
echo "waxman multicast edge"
for i in {1..10}; do ./benchmark.py --vtime --edge --waxman --multicast; done
echo "waxman shortest edge"
for i in {1..10}; do ./benchmark.py --vtime --edge --waxman --shortest; done
echo "smallworld multicast edge"
for i in {1..10}; do ./benchmark.py --vtime --edge --smallworld --multicast; done
echo "smallworld shortest edge"
for i in {1..10}; do ./benchmark.py --vtime --edge --smallworld --shortest; done
echo "fattree multicast edge"
for i in {1..10}; do ./benchmark.py --vtime --edge --fattree --multicast; done
echo "fattree shortest edge"
for i in {1..10}; do ./benchmark.py --vtime --edge --fattree --shortest; done
