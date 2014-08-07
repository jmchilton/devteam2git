#!/usr/bin/env python
# Usage:
#   python dev2git.py build
# Builds a potential mega-repository for Galaxy devteam tools.

import argparse
import tempfile
from fabric.api import local
from fabric.context_managers import lcd
from bioblend import toolshed

TOOLSHED = "https://toolshed.g2.bx.psu.edu"
OWNER = "devteam"

tempdir = tempfile.mkdtemp()

EXCLUDE_REPOS = [
    # These have real homes elsewhere...
    "ncbi_blast_plus",
    "blast_datatypes",
    "freebayes",
    # Deprecated repos that devteam does not intend to maintain...
    "freebayes_wrapper",
    # This is empty and crashes the script...
    "star",
]

NEST_REPOS = {
    "gatk": [
        "analyze_covariates",
        "count_covariates",
        "depth_of_coverage",
        "indel_realigner",
        "print_reads",
        "realigner_target_creator",
        "table_recalibration",
        "unified_genotyper",
        "variant_annotator",
        "variant_apply_recalibration",
        "variant_combine",
        "variant_eval",
        "variant_filtration",
        "variant_recalibrator",
        "variant_select",
        "variants_validate",
    ],
    "gops": [
        "basecoverage",
        "cluster",
        "complement",
        "concat",
        "coverage",
        "flanking_features",
        "get_flanks",
        "intersect",
        "join",
        "merge",
        "subtract",
        "subtract_query",
        "tables_arithmetic_operations",
    ],
    "fastx_toolkit": [
        "fasta_clipping_histogram",
        "fasta_formatter",
        "fasta_nucleotide_changer",
        "fastq_quality_boxplot",
        "fastq_quality_converter",
        "fastq_quality_filter",
        "fastq_to_fasta",
        "fastx_artifacts_filter",
        "fastx_barcode_splitter",
        "fastx_clipper",
        "fastx_collapser",
        "fastx_nucleotides_distribution",
        "fastx_quality_statistics",
        "fastx_renamer",
        "fastx_reverse_complement",
        "fastx_trimmer",
    ],
    "samtools": [
        "bam_to_sam",
        "pileup_interval",
        "sam_to_bam",
        "samtools_flagstat",
        "samtools_phase",
        "samtools_rmdup",
        "samtools_mpileup",
        "samtools_slice_bam",
    ],
    # These packages have old-style "metapackages" predating repository_suite_definitions
    "cufflinks": [
        "cufflinks",
        "cuffcompare",
        "cuffmerge",
        "cuffdiff",
    ],
    "vcftools": [
        "vcftools_annotate",
        "vcftools_compare",
        "vcftools_isec",
        "vcftools_merge",
        "vcftools_slice",
        "vcftools_subset",
    ],
    # These tools don't even have metapackages but I'm trying to control the size of the folder
    # by grouping them together. Really open to reshuffling this structure.
    "hgv": [
        "hgv_hilbertvis",
        "snpfreq",
        "hgv_fundo",
    ],
    "galaxy_sequence_utils": [
        "fastq_trimmer",
        "fastq_to_tabular",
        "fastq_combiner",
        "fastq_paired_end_splitter",
        "fastq_manipulation",
        "fastqtofasta",
        "fastq_masker_by_quality",
        "tabular_to_fastq",
        "fastq_paired_end_deinterlacer",
        "fastq_paired_end_interlacer",
        "fastq_stats",
        "fastq_groomer",
        "fastq_filter",
        "fastq_paired_end_joiner",
    ],
    "taxonomy": [
        "gi2taxonomy",
        "find_diag_hits",
        "t2ps",
        "poisson2test",
        "lca_wrapper",
        "t2t_report",
    ]
}

SUDO_REPOSITORY_SUITES = [ "all_cufflinks_tool_suite", "all_vcftools" ]


def list():
    repos = dev_repos()
    map( summarize_repo, repos )


def build():
    execute("rm -rf repo")
    execute("mkdir repo")
    with lcd("repo"):
        # vis will be empty, needs a gitignore file
        execute("mkdir -p tools tool_collections suites packages datatypes data_managers visualisations")
        execute("git init .")
        for repo in dev_repos():
            repo_name = repo[ "name" ]
            repo_type = repo[ "type" ]
            if repo_name in EXCLUDE_REPOS:
                continue
            if repo_type == "tool_dependency_definition":
                clone_package(repo)
            elif repo_type == "repository_suite_definition" or repo["name"] in SUDO_REPOSITORY_SUITES:
                clone_suite(repo)
            elif repo_type == "unrestricted":
                if repo["name"].find('data_manager') != -1:
                    clone_data_managers(repo)
                elif repo["name"].find('datatype') != -1:
                    clone_datatypes(repo)
                else:
                    clone_tool(repo)
            else:
                print "WARN: Unhandled repo type %s" % repo_type


def clone_datatypes(repo):
    with lcd("datatypes"):
        clone_repo(repo)


def clone_data_managers(repo):
    with lcd("data_managers"):
        clone_repo(repo)


def clone_package(repo):
    with lcd("packages"):
        clone_repo(repo)


def clone_tool(repo):
    collection_name = get_repo_collection(repo)
    if collection_name:
        with lcd("tool_collections"):
            execute("mkdir -p %s" % collection_name)
            with lcd(collection_name):
                clone_repo(repo)
    else:
        with lcd("tools"):
            clone_repo(repo)


def clone_suite(repo):
    with lcd("suites"):
        clone_repo(repo)


def dev_repos():
    ts = toolshed.ToolShedInstance(url=TOOLSHED)
    repos = ts.repositories.get_repositories()
    repos = [r for r in repos if r["owner"] == OWNER]
    return repos


def clone_repo(repo):
    repository_url = "%s/repos/%s/%s" % (TOOLSHED, repo["owner"], repo["name"])
    directory_name = destination_directory(repo)
    execute("hg clone %s %s/%s" % (repository_url, tempdir, repo["name"]))
    execute("mkdir -p %s" % directory_name)
    with lcd(directory_name):
        execute("cp -r %s/%s/* ." % (tempdir, repo["name"]))
        execute("rm -rf %s/%s" % (tempdir, repo["name"]))
        execute("rm -rf .hg")
        execute("git add .")
        msg1 = "Initial import of tool shed repository %s" % repo["name"]
        msg2 = "See %s for previous commit history." % repository_url
        execute('''git commit --author="devteam <galaxy-lab@bx.psu.edu>" -m "%s" -m "%s"''' % (msg1, msg2))


def destination_directory(repo):
    destination = repo["name"]  # By default just keep in same directory name..

    # Was trying to merge the repositories so macro files, wrappers, and
    # tool-data, etc.. weren't duplicated - but it looks like Dave B. has
    # done a meticulous job separating out test-data into the correct repo
    # so I guess it might be best to just keep it one directory per repo here
    # and go through later and replace things with symbolic links which would
    # be resolved when uploading tar balls to the tool shed.

    #for suite, repos in NEST_REPOS.iteritems():
    #    if destination in repos:
    #        destination = suite
    #        break
    return destination


def get_repo_collection(repo):
    name = repo["name"]  # By default just keep in same directory name..
    for collection_name, repos in NEST_REPOS.iteritems():
        if name in repos:
            return collection_name
    return None


def summarize_repo(repo):
    print "name: %s, type %s, id %s" % ( repo[ "name" ], repo["type"], repo["id"] )


def execute(cmd):
    local(cmd)


def main():
    global TOOLSHED

    parser = argparse.ArgumentParser()
    parser.add_argument('action', metavar='action', type=str)
    parser.add_argument('--shed', type=str, default="main")
    args = parser.parse_args()
    if args.shed == "dev":
        TOOLSHED = "https://testtoolshed.g2.bx.psu.edu"
    eval(args.action)()


if __name__ == "__main__":
    main()
