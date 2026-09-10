CXX ?= c++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra

.PHONY: all test clean
all: build/generate build/audit build/audit_intervals build/reference

build:
	mkdir -p build

build/generate: src/generate.cpp | build
	$(CXX) $(CXXFLAGS) -pthread $< -o $@

build/audit: src/audit.cpp src/audit_histogram.hpp | build
	$(CXX) $(CXXFLAGS) -pthread $< -o $@

build/audit_intervals: src/audit_intervals.cpp src/audit_histogram.hpp | build
	$(CXX) $(CXXFLAGS) -pthread $< -o $@

build/test_audit_histogram: tests/audit_histogram.cpp src/audit_histogram.hpp | build
	$(CXX) $(CXXFLAGS) $< -o $@

build/reference: reference/segmented.cpp | build
	$(CXX) $(CXXFLAGS) $< -o $@

test: all build/test_audit_histogram
	python3 -m unittest discover -s tests -v

clean:
	rm -rf build
