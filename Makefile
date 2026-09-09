CXX ?= c++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra

.PHONY: all test clean
all: build/generate build/audit build/reference

build:
	mkdir -p build

build/generate: src/generate.cpp | build
	$(CXX) $(CXXFLAGS) -pthread $< -o $@

build/audit: src/audit.cpp | build
	$(CXX) $(CXXFLAGS) -pthread $< -o $@

build/reference: reference/segmented.cpp | build
	$(CXX) $(CXXFLAGS) $< -o $@

test: all
	python3 -m unittest discover -s tests -v

clean:
	rm -rf build
