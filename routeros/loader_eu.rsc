# RouterOS v7 loader for iplist resources (EU)
# Update URL after repository publish.

:local listName "blacklist_eu"
:global resources {
  "cloudflare";
}

:log info ("iplist: start loader list=" . $listName . " resources=" . [:len $resources])

:if ([:len $resources] = 0) do={
  :log info "iplist: no resources configured for EU"
  :return
}

:local minBytes 200

:foreach resource in=$resources do={
  :do {
    :log info ("iplist: fetching resource=" . $resource)
    :local url ("https://raw.githubusercontent.com/REPLACE_USER/MikroTik_ASN_IPList/main/dist/" . $resource . ".rsc")
    :local tmpFile ("iplist_" . $resource . ".rsc.tmp")

    /tool fetch url=$url mode=https dst-path=$tmpFile keep-result=yes

    :if ([:len [/file find name=$tmpFile]] = 0) do={
      :log warning ("iplist: missing file for " . $resource)
      :error "missing file"
    }

    :local size [/file get $tmpFile size]
    :if ($size < $minBytes) do={
      :log warning ("iplist: file too small for " . $resource . " size=" . $size)
      :error "file too small"
    }

    :local contents [/file get $tmpFile contents]
    :if ([:find $contents "# iplist-rsc v1"] = nil) do={
      :log warning ("iplist: missing sentinel for " . $resource)
      :error "missing sentinel"
    }

    :if ([:find $contents ("# resource=" . $resource)] = nil) do={
      :log warning ("iplist: resource mismatch for " . $resource)
      :error "resource mismatch"
    }

    :if ([:find $contents ":global AddressList"] = nil) do={
      :log warning ("iplist: AddressList missing for " . $resource)
      :error "AddressList missing"
    }

    :log info ("iplist: removing old entries resource=" . $resource)
    :local tag ("iplist:auto:" . $resource)
    :foreach i in=[/ip/firewall/address-list find] do={
      :if ([/ip/firewall/address-list get $i comment] = $tag) do={
        /ip/firewall/address-list remove $i
      }
    }

    :log info ("iplist: importing resource=" . $resource . " size=" . $size)
    :global AddressList $listName
    /import file-name=$tmpFile
    /file remove $tmpFile
    :log info ("iplist: loaded resource=" . $resource)
  } on-error={
    :log warning ("iplist: skipped resource due to error: " . $resource)
  }
}
