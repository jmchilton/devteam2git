# TODO: Try to merge suites into a single directory in github.
# TODO(?): Preserve history.
import argparse
import tempfile
from fabric.api import local
from fabric.context_managers import lcd
from bioblend import toolshed

TOOLSHED = "https://toolshed.g2.bx.psu.edu"
OWNER = "devteam"

tempdir = tempfile.mkdtemp()

MERGE_REPOS = {
    "suite_gatk": [
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
    "suite_gops": [
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
    "suite_fastx_toolkit": [
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
    "suite_samtools": [
        "data_manager_sam_fasta_index_builder",
        "bam_to_sam",
        "pileup_interval",
        "sam_to_bam",
        "samtools_flagstat",
        "samtools_phase",
        "samtools_rmdup",
        "samtools_mpileup",
        "samtools_slice_bam",
    ],
}


def list():
    repos = dev_repos()
    map( summarize_repo, repos )


def build():
    execute("rm -rf repo")
    execute("mkdir repo")
    with lcd("repo"):
        execute("mkdir tools suites packages datatypes data_managers visualisations") #vis will be empty, needs a gitignore file
        execute("git init .")
        for repo in dev_repos():
            repo_type = repo[ "type" ]
            if repo_type == "tool_dependency_definition":
                clone_package(repo)
            elif repo_type == "unrestricted":
                if repo["name"].find('data_manager') != -1:
                    clone_data_managers(repo)
                elif repo["name"].find('datatype') != -1:
                    clone_datatypes(repo)
                else:
                    clone_tool(repo)
            elif repo_type == "repository_suite_definition":
                clone_suite(repo)
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
    for suite, repos in MERGE_REPOS.iteritems():
        if destination in repos:
            destination = suite
            break
    return destination


def summarize_repo(repo):
    print "name: %s, type %s, id %s" % ( repo[ "name" ], repo["type"], repo["id"] )


def execute(cmd):
    local(cmd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', metavar='action', type=str)
    args = parser.parse_args()
    eval(args.action)()


if __name__ == "__main__":
    main()
