# RouterOS v7 loader for iplist resources (EU)
# Update URL after repository publish.

:local scope "EU"
:local listName "blacklist_eu"
:local runId ("" . [/system/clock get date] . " " . [/system/clock get time])
:global resources {
  "cloudflare";
}

:log info ("iplist: event=start scope=" . $scope . " list=" . $listName . " resources_count=" . [:len $resources] . " runId=" . $runId)

:if ([:len $resources] = 0) do={
  :log info ("iplist: event=skip scope=" . $scope . " list=" . $listName . " reason=empty_resources runId=" . $runId)
  :return
}

:local minBytes 200

:foreach resource in=$resources do={
  :if ([:find $resource " "] != nil) do={
    :log warning ("iplist: event=skip scope=" . $scope . " list=" . $listName . " resource=" . $resource . " reason=bad_resource_whitespace runId=" . $runId)
  } else={
    :local stage "init"
    :do {
      :local url ("https://raw.githubusercontent.com/REPLACE_USER/MikroTik_ASN_IPList/main/dist/" . $resource . ".rsc")
      :local tmpFile ("iplist_" . $resource . ".rsc.tmp")

      :set stage "fetch"
      :log info ("iplist: event=fetch scope=" . $scope . " list=" . $listName . " resource=" . $resource . " url=" . $url . " runId=" . $runId)
      /tool fetch url=$url mode=https dst-path=$tmpFile keep-result=yes

      :set stage "validate"
      :if ([:len [/file find name=$tmpFile]] = 0) do={
        :log warning ("iplist: event=validate_fail scope=" . $scope . " list=" . $listName . " resource=" . $resource . " reason=missing_file runId=" . $runId)
        :error "missing file"
      }

      :local size [/file get $tmpFile size]
      :if ($size < $minBytes) do={
        :log warning ("iplist: event=validate_fail scope=" . $scope . " list=" . $listName . " resource=" . $resource . " reason=file_too_small size=" . $size . " runId=" . $runId)
        :error "file too small"
      }

      :local contents [/file get $tmpFile contents]
      :if ([:find $contents "# iplist-rsc v1"] = nil) do={
        :log warning ("iplist: event=validate_fail scope=" . $scope . " list=" . $listName . " resource=" . $resource . " reason=sentinel_missing runId=" . $runId)
        :error "missing sentinel"
      }

      :if ([:find $contents ("# resource=" . $resource)] = nil) do={
        :log warning ("iplist: event=validate_fail scope=" . $scope . " list=" . $listName . " resource=" . $resource . " reason=resource_mismatch runId=" . $runId)
        :error "resource mismatch"
      }

      :if ([:find $contents ":global AddressList"] = nil) do={
        :log warning ("iplist: event=validate_fail scope=" . $scope . " list=" . $listName . " resource=" . $resource . " reason=addresslist_decl_missing runId=" . $runId)
        :error "AddressList missing"
      }

      :log info ("iplist: event=validate_ok scope=" . $scope . " list=" . $listName . " resource=" . $resource . " size=" . $size . " runId=" . $runId)

      :local tag ("iplist:auto:" . $resource)
      :local removed 0
      :foreach i in=[/ip/firewall/address-list find] do={
        :if ([/ip/firewall/address-list get $i comment] = $tag) do={
          /ip/firewall/address-list remove $i
          :set removed ($removed + 1)
        }
      }
      :log info ("iplist: event=remove scope=" . $scope . " list=" . $listName . " resource=" . $resource . " removed=" . $removed . " runId=" . $runId)

      :set stage "import"
      :global AddressList $listName
      /import file-name=$tmpFile
      /file remove $tmpFile
      :log info ("iplist: event=import_ok scope=" . $scope . " list=" . $listName . " resource=" . $resource . " bytes=" . $size . " total=" . [:len [/ip/firewall/address-list find where comment=$tag]] . " runId=" . $runId)
    } on-error={
      :local reason "unknown"
      :if ($stage = "fetch") do={ :set reason "fetch_failed" }
      :if ($stage = "import") do={ :set reason "import_failed" }
      :if ($stage = "validate") do={ :set reason "validate_failed" }
      :log warning ("iplist: event=skip scope=" . $scope . " list=" . $listName . " resource=" . $resource . " reason=" . $reason . " err=" . $message . " runId=" . $runId)
    }
  }
}
