#!/usr/bin/env python3

import time

import pytest

import helpers.keeper_utils as keeper_utils
from helpers.cluster import ClickHouseCluster
from helpers.network import PartitionManager

cluster = ClickHouseCluster(__file__)
node1 = cluster.add_instance(
    "node1",
    main_configs=["configs/enable_keeper1.xml", "configs/use_keeper.xml"],
    stay_alive=True,
)
node2 = cluster.add_instance(
    "node2",
    main_configs=["configs/enable_keeper2.xml", "configs/use_keeper.xml"],
    stay_alive=True,
)


@pytest.fixture(scope="module")
def started_cluster():
    try:
        cluster.start()

        yield cluster

    finally:
        cluster.shutdown()


def smaller_exception(ex):
    return "\n".join(str(ex).split("\n")[0:2])


def wait_nodes():
    keeper_utils.wait_nodes(cluster, [node1, node2])


def get_fake_zk(nodename, timeout=30.0):
    return keeper_utils.get_fake_zk(cluster, nodename, timeout=timeout)


def test_read_write_two_nodes(started_cluster):
    try:
        wait_nodes()
        node1_zk = get_fake_zk("node1")
        node2_zk = get_fake_zk("node2")

        node1_zk.create("/test_read_write_multinode_node1", b"somedata1")
        node2_zk.create("/test_read_write_multinode_node2", b"somedata2")

        # stale reads are allowed
        while node1_zk.exists("/test_read_write_multinode_node2") is None:
            time.sleep(0.1)

        # stale reads are allowed
        while node2_zk.exists("/test_read_write_multinode_node1") is None:
            time.sleep(0.1)

        assert node2_zk.get("/test_read_write_multinode_node1")[0] == b"somedata1"
        assert node1_zk.get("/test_read_write_multinode_node1")[0] == b"somedata1"

        assert node2_zk.get("/test_read_write_multinode_node2")[0] == b"somedata2"
        assert node1_zk.get("/test_read_write_multinode_node2")[0] == b"somedata2"

    finally:
        try:
            for zk_conn in [node1_zk, node2_zk]:
                zk_conn.stop()
                zk_conn.close()
        except:
            pass


def test_read_write_two_nodes_with_blocade(started_cluster):
    try:
        wait_nodes()
        node1_zk = get_fake_zk("node1", timeout=5.0)
        node2_zk = get_fake_zk("node2", timeout=5.0)

        print("Blocking nodes")
        with PartitionManager() as pm:
            pm.partition_instances(node2, node1)

            # We will respond conection loss but process this query
            # after blocade will be removed
            with pytest.raises(Exception):
                node1_zk.create("/test_read_write_blocked_node1", b"somedata1")

            # This node is not leader and will not process anything
            with pytest.raises(Exception):
                node2_zk.create("/test_read_write_blocked_node2", b"somedata2")

        print("Nodes unblocked")
        for i in range(10):
            try:
                node1_zk = get_fake_zk("node1")
                node2_zk = get_fake_zk("node2")
                break
            except:
                time.sleep(0.5)

        for i in range(100):
            try:
                node1_zk.create("/test_after_block1", b"somedata12")
                break
            except:
                time.sleep(0.1)
        else:
            raise Exception("node1 cannot recover after blockade")

        print("Node1 created it's value")

        for i in range(100):
            try:
                node2_zk.create("/test_after_block2", b"somedata12")
                break
            except:
                time.sleep(0.1)
        else:
            raise Exception("node2 cannot recover after blockade")

        print("Node2 created it's value")

        # stale reads are allowed
        while node1_zk.exists("/test_after_block2") is None:
            time.sleep(0.1)

        # stale reads are allowed
        while node2_zk.exists("/test_after_block1") is None:
            time.sleep(0.1)

        assert node1_zk.exists("/test_after_block1") is not None
        assert node1_zk.exists("/test_after_block2") is not None
        assert node2_zk.exists("/test_after_block1") is not None
        assert node2_zk.exists("/test_after_block2") is not None

    finally:
        try:
            for zk_conn in [node1_zk, node2_zk]:
                zk_conn.stop()
                zk_conn.close()
        except:
            pass
