#ifndef SimIO_h
#define SimIO_h 1

#include "structures.hh"

#include <cstdint>
#include <string>
#include <vector>

namespace SimIO {

/// Semantic row aliases shared between simulation logic and IO.
using PrimaryInfo = SimStructures::PrimaryInfo;
using SecondaryInfo = SimStructures::SecondaryInfo;
using PhotonInfo = SimStructures::PhotonInfo;

struct OutputPaths {
  std::string primaries;
  std::string secondaries;
  std::string photons;
};

struct OutputSelection {
  bool primaries = true;
  bool secondaries = true;
  bool photons = true;
};

/// Initialize binary output files (validates parent directories exist)
bool InitOutput(const OutputPaths& paths,
                const OutputSelection& selection,
                std::string* errorMessage);

/// Append rows to binary output files (three separate files with fixed-size records)
bool AppendOutput(const OutputPaths& paths,
                  const OutputSelection& selection,
                  const std::vector<PrimaryInfo>& primaryRows,
                  const std::vector<SecondaryInfo>& secondaryRows,
                  const std::vector<PhotonInfo>& photonRows,
                  std::string* errorMessage);

/// Close binary output file handles for the current thread.
void CloseOutput(const std::string& outputPath);

}  // namespace SimIO

#endif
