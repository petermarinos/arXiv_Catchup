"""Unit tests on xml loading handling functions."""

# Import libraries
import xml.etree.ElementTree as ET
import unittest
import logging
import typing

# Import functions to test
from scripts.xml_handling import (
    extract_paper_id_version,
    extract_paper_links,
    extract_paper_textfields,
    extract_paper_cats,
    extract_paper_authors,
)


class TestXmlHandling(unittest.TestCase):
    """Test the XML file loading and handling"""

    def setUp(self):
        """Set up the tests by loading the test .xml file and defining some constants."""

        self.logger = logging.getLogger()

        self.ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        self.xml_tree = typing.cast(ET.ElementTree, ET.parse("./tests/test.xml"))

        self.entry = self.xml_tree.findall("atom:entry", self.ns)[0]

    def test_paper_id_version_revision(self):
        """Test the extraction of the ID number, version number, and the revision bool."""

        id_num, version, updated, published, revised = extract_paper_id_version(
            self.logger, self.ns, self.entry
        )

        self.assertEqual(id_num, "2602.17652")
        self.assertEqual(version, 1)
        self.assertEqual(updated, "2026-02-19T18:56:28Z")
        self.assertEqual(published, "2026-02-19T18:56:28Z")
        self.assertEqual(revised, False)

    def test_paper_links(self):
        """Test the extraction of the two arXiv links."""

        link_abs, link_pdf = extract_paper_links(self.logger, self.ns, self.entry)

        self.assertEqual(link_abs, "https://arxiv.org/abs/2602.17652v1")
        self.assertEqual(link_pdf, "https://arxiv.org/pdf/2602.17652v1")

    def test_paper_text(self):
        """Test the extraction of the title and abstract."""

        title, abstract, comment, n_words_title, n_words_abstract = (
            extract_paper_textfields(self.logger, self.ns, self.entry)
        )

        self.assertEqual(
            title,
            (
                "A Chemodynamical Census of the Milky Way's Ultra-Faint Compact Satellites. I. A "
                "First Population-Level Look at the Internal Kinematics and Metallicities of 19 "
                "Extremely-Low-Mass Halo Stellar Systems"
            ),
        )
        self.assertEqual(
            abstract,
            (
                "Deep, wide-area photometric surveys have uncovered a population of compact "
                r"($r_{1/2} \approx$ 1-15 pc), extremely-low-mass ($M_* \approx$ 20-4000 "
                r"$M_{\odot}$) stellar systems in the Milky Way halo that are smaller in size than "
                "known ultra-faint dwarf galaxies (UFDs) and substantially fainter than most "
                "classical globular clusters (GCs). Very little is known about the nature and "
                'origins of this population of "Ultra-Faint Compact Satellites" (UFCSs) owing to a '
                "dearth of spectroscopic measurements. Here, we present the first spectroscopic "
                "census of these compact systems based on Magellan/IMACS and Keck/DEIMOS "
                r"observations of 19 individual UFCSs, representing $\sim$2/3 of the known "
                "population. We securely measure mean radial velocities for all 19 systems, "
                "velocity dispersions for 15 (predominantly upper limits), metallicities for 17, "
                r"metallicity dispersions for 8, and $\textit{Gaia}$-based mean proper motions for "
                "18. This large new spectroscopic sample provides the first insights into "
                "population-level trends for these extreme satellites. We demonstrate that: (1) "
                "the UFCSs are kinematically colder, on average, than the UFDs, disfavoring very "
                "dense dark matter halos in most cases, (2) the UFCS population is chemically "
                r"diverse, spanning a factor of $\sim$300 in mean iron abundance ($\rm -3.3 "
                r"\lesssim [Fe/H] \lesssim -0.8$), with multiple systems falling beneath the "
                '"metallicity floor" proposed for GCs, and (3) while some higher-metallicity '
                "and/or younger UFCSs are clearly star clusters, the dynamical and/or chemical "
                r"evidence allows the possibility that up to $\sim$50% of the UFCSs in our sample "
                "(9 of 19) may represent the smallest and least-massive galaxies yet discovered."
            ),
        )
        self.assertEqual(
            comment,
            (
                "63 pages (main) + 18 pages (references + appendix), 30 Figures, 6 Tables. Will "
                "submit to ApJ in one week; comments welcome. Brief summary available here: "
                "https://wcerny.github.io/compactsatellites/. Repository with spectroscopic member "
                "catalogs: https://zenodo.org/records/18612486. Forthcoming Paper II will explore "
                "the orbits, accretion histories, and tidal influences of the same sample"
            ),
        )
        self.assertEqual(n_words_title, 31)  # <- fail, counts "'s" as a word
        self.assertEqual(
            n_words_abstract, 242
        )  # <- fails, counts each character in maths mode as a separate word

    def test_paper_cats(self):
        """Test the extraction of the paper's categories."""
        # add another category to the test .xml file

        category = extract_paper_cats(self.logger, self.ns, self.entry)

        self.assertEqual(category, ["astro-ph.GA"])

    def test_paper_authors(self):
        """Test the extraction of the paper's authors."""

        author_list, n_authors = extract_paper_authors(self.logger, self.ns, self.entry)

        self.assertEqual(
            author_list,
            [
                "William Cerny",
                "Ting S. Li",
                "Andrew B. Pace",
                "Joshua D. Simon",
                "Marla Geha",
                "Alexander P. Ji",
                "Alex Drlica-Wagner",
                "Jordan Bruce",
                "Oleg Y. Gnedin",
                "Eric F. Bell",
                "Sidney Mau",
                "Ivanna Escala",
                "Daisy Bissonette",
                "Alessandro Savino",
                "Anirudh Chiti",
                "Evan N. Kirby",
            ],
        )
        self.assertEqual(n_authors, 16)


if __name__ == "__main__":
    unittest.main()
