#!/usr/bin/env python
# Usage:
#   python dev2git.py build
# Builds a potential mega-repository for Galaxy devteam tools.

import argparse
import tempfile
import shutil
from fabric.api import local
from fabric.context_managers import lcd
from bioblend import toolshed

TOOLSHED = "https://toolshed.g2.bx.psu.edu"
OWNER = "devteam"
RESUME = False

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
    if not RESUME:
        execute("rm -rf repo")
        execute("mkdir repo")

    with lcd("repo"):
        # vis will be empty, needs a gitignore file
        if not RESUME:
            execute("git init .")
            execute('touch README')
            execute('git add README')
            execute('''git commit --author="devteam <galaxy-lab@bx.psu.edu>" -m "Add empty README to the master branch"''')

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
    directory_name = "datatypes/%s" % repo['name']
    clone_repo(repo, directory_name)


def clone_data_managers(repo):
    directory_name = "data_managers/%s" % repo['name']
    clone_repo(repo, directory_name)


def clone_package(repo):
    directory_name = "packages/%s" % repo['name']
    clone_repo(repo, directory_name)


def clone_tool(repo):
    collection_name = get_repo_collection(repo)
    if collection_name:
        directory_name = "tool_collections/%s/%s" % (collection_name, repo['name'])
        clone_repo(repo, directory_name)
    else:
        directory_name = "tools/%s" % repo['name']
        clone_repo(repo, directory_name)


def clone_suite(repo):
    directory_name = "suites/%s" % repo['name']
    clone_repo(repo, directory_name)


def dev_repos():
    ts = toolshed.ToolShedInstance(url=TOOLSHED)
    repos = ts.repositories.get_repositories()
    repos = [r for r in repos if r["owner"] == OWNER]
    return repos


def clone_repo(repo, directory_name):
    # TODO: something in here with RESUME to make the option actually work.
    repository_url = "%s/repos/%s/%s" % (TOOLSHED, repo["owner"], repo["name"])
    execute("git checkout --orphan %s" % repo['name'])
    execute('git rm -rf .')
    execute("git clone 'hg::%s' %s/%s" % (repository_url, tempdir, repo['name']))
    execute("git pull %s/%s" % (tempdir, repo['name']))
    execute("rm -rf %s/%s" % (tempdir, repo['name']))
    execute("mkdir -p %s" % directory_name)
    execute("git filter-branch -f --tree-filter 'mkdir -p %s; git ls-tree --name-only $GIT_COMMIT | xargs -I files mv files %s'" % (directory_name, directory_name))
    execute('git checkout master')
    execute("""git merge -m "Merging tool shed devteam repository %s." %s""" % (repo['name'], repo['name']))
    execute("git branch -d %s" % repo['name'])


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
    global TOOLSHED, RESUME

    parser = argparse.ArgumentParser()
    parser.add_argument('action', metavar='action', type=str)
    parser.add_argument('--shed', type=str, default="main")
    parser.add_argument('--resume', action="store_true", default=False)

    args = parser.parse_args()
    if args.shed == "dev":
        TOOLSHED = "https://testtoolshed.g2.bx.psu.edu"
    if args.resume:
        RESUME = True
    try:
        eval(args.action)()
    finally:
        shutil.rmtree(tempdir)


if __name__ == "__main__":
    main()
