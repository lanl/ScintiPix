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

struct HDF5OutputPaths {
  std::string primaries;
  std::string secondaries;
  std::string photons;
};

struct HDF5OutputSelection {
  bool primaries = true;
  bool secondaries = true;
  bool photons = true;
};

/// Initialize HDF5 output files (call once at run start, before workers begin)
bool InitHDF5(const HDF5OutputPaths& paths,
              const HDF5OutputSelection& selection,
              std::string* errorMessage);

/// Append rows to HDF5 datasets (three separate files)
bool AppendHDF5(const HDF5OutputPaths& paths,
                const HDF5OutputSelection& selection,
                const std::vector<PrimaryInfo>& primaryRows,
                const std::vector<SecondaryInfo>& secondaryRows,
                const std::vector<PhotonInfo>& photonRows,
                std::string* errorMessage);

/// Close HDF5 file handles for given output path
void CloseHDF5(const std::string& hdf5Path);

}  // namespace SimIO

#endif
