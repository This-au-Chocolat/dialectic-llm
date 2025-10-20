from prefect import flow, task


@task
def thesis(x):
    return {"answer": "...", "meta": {}}


@task
def antithesis(t):
    return {"critique": "...", "meta": {}}


@task
def synthesis(t, a):
    return {"answer": "...", "meta": {}}


@flow(name="tas_k1")
def run_tas_k1(item):
    t = thesis.submit(item)
    a = antithesis.submit(t)
    s = synthesis.submit(t, a)
    return s


if __name__ == "__main__":
    print(run_tas_k1("demo"))
