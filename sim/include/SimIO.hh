#ifndef SimIO_h
#define SimIO_h 1

#include "structures.hh"

#include <string>
#include <vector>

namespace SimIO {

/// Semantic row aliases shared between simulation logic and IO.
using PrimaryInfo = SimStructures::PrimaryInfo;
using SecondaryInfo = SimStructures::SecondaryInfo;
using PhotonInfo = SimStructures::PhotonInfo;

struct ParquetOutputPaths {
  std::string primaries;
  std::string secondaries;
  std::string photons;
};

/// Normalize run name for filesystem-safe directory usage.
std::string NormalizeRunName(const std::string& value);

/// Strip known output suffixes when present.
std::string StripKnownOutputExtension(const std::string& value);

/// Compose absolute output file path with run/output-path routing rules.
std::string ComposeOutputPath(const std::string& base,
                              const std::string& outputPath,
                              const std::string& runName,
                              const char* extension);

ParquetOutputPaths ParquetPathsForBase(const std::string& basePath);

/// Write primary/secondary/photon rows as separate Parquet tables.
bool WriteParquet(const std::string& basePath,
                  const std::vector<PrimaryInfo>& primaryRows,
                  const std::vector<SecondaryInfo>& secondaryRows,
                  const std::vector<PhotonInfo>& photonRows,
                  std::string* errorMessage);

}  // namespace SimIO

#endif
